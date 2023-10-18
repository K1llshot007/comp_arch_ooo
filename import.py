import sys
import re
import logging
import pdb

# Hold information about a single instruction.
# Also store additional information about allowed kinds of instructions.
class instruction:


    def __init__ (self, insNumber, inst, op1, op2, op3):
        self.insNumber = insNumber
        self.inst = inst

        # self.operand

        # We only allow 4 instructions for now.
        if inst == "I":
            self.srcReg1 = op2
            self.srcReg2 = None
            self.immediate = op3
            self.destReg = op1
            self.memAccess = False
        elif inst == "R":
            self.srcReg1 = op2
            self.srcReg2 = op3
            self.immediate = None
            self.destReg = op1
            self.memAccess = False
        elif inst == "L":
            self.srcReg1 = op3
            self.srcReg2 = None
            self.immediate = op3
            self.destReg = op1
            self.memAccess = True
        elif inst == "S":
            self.srcReg1 = op1
            self.srcReg2 = op3
            self.immediate = op2
            self.destReg = None
            self.memAccess = True

        self.overwritten = None

        # Initially, every instruction is not renamed.
        self.renamed = False

        # Initially, this instruction is not scheduled
        self.fetchCycle = None
        self.decodeCycle = None
        self.renameCycle = None
        self.dispatchCycle = None
        self.issueCycle = None
        self.writebackCycle = None
        self.commitCycle = None

    def isLoadInst (self):
        return self.inst == "L"

    def isStoreInst (self):
        return self.inst == "S"

    def isLoadStoreInst (self):
        return self.isLoadInst() or self.isStoreInst()

    def hasIssued (self):
        return self.issueCycle is not None

    def hasWrittenback (self):
        return self.writebackCycle is not None

    def hasCommitted (self):
        return self.commitCycle is not None

    def __str__ (self):
        return "[inst %d: %s [%s%s]%s -> %s]" % (
            self.insNumber,
            self.inst,
            self.srcReg1,
            "" if self.srcReg2 is None else (" " + str(self.srcReg2)),
            " #%d" % (self.immediate) if self.immediate is not None else "",
            self.destReg
        )
        

# A generic pipeline stage.
class pipelineStage:


    def __init__ (self, width):
        self.queue = []

    def pushIt (self, item):
        self.queue.append(item)

    def insertIt (self, item):
        self.queue.insert(0, item)

    def isEmpty (self):
        return len(self.queue) == 0

    def popIt (self):
        if self.isEmpty():
            raise TypeError("Pull from empty pipeline stage")

        return self.queue.pop(0)

    def __str__ (self):
        return "[pipelineStage %s]" % (self.queue)



# Data structure to hold architecture to physical register mapping.
class regMap:


    def __init__ (self, numArchReg):
        # Initial mapping for all arch registers is None.
        self.numArchReg = numArchReg
        self.mappingTable = [None] * self.numArchReg

    def put (self, archRegNum, phyRegNum):
        self.mappingTable[archRegNum] = phyRegNum

    def get (self, archRegNum):
        return self.mappingTable[archRegNum]

    def __str__ (self):
        return "[regMap %s]" % (self.mappingTable)



# Data structure to hold free list physical registers
class freeList:

    
    def __init__ (self, numPhysReg):
        # Initialize free list with ALL physical registers.
        self.freeListMap = list(range(numPhysReg))

    def isFree (self):
        return len(self.freeListMap)
    
    def getFreeReg (self):
        if not self.isFree():
            return TypeError("No free registers")
        
        return self.freeListMap.pop(0)

    def free (self, regNum):
        self.freeListMap.append(regNum)

    def __str__ (self):
        return "[freeListMap %s]" % (self.freeListMap)


# Data structure to track "ready" status of physical registers.
class readyQueue:


    def __init__ (self, numPhysReg):
        # Initialize all physical registers as ready.
        self.table = [True] * numPhysReg

    def isReady (self, regNum):
        return self.table[regNum]

    def ready (self, regNum):
        self.table[regNum] = True

    def clear (self, regNum):
        self.table[regNum] = False

    def __str__ (self):
        return "[readyQueue %s]" % (
            "".join(map(lambda x: "1" if x else "0", self.table))
        )


# The load/store queue.
class loadStoreQueue:


    def __init__  (self):
        self.entries = []

    def append (self, inst):
        self.entries.append(inst)

    def remove (self, inst):
        self.entries.remove(inst)

    # Check if a given L/S instruction can be executed.
    def canExecute (self, inst):
        # Iterate all entres in LSQ.
        for (index, currentInstr) in enumerate(self.entries):

            # All Load instructions can be executed until we hit a store instruction in LSQ.
            # Store instruction can only be executed if it is at the head.
            if currentInstr.isLoadInst() or (currentInstr.isStoreInst() and index == 0):
                if currentInstr == inst:
                    return True

            if currentInstr.isStoreInst():
                break

        return False

    # Get list of all L/S instructions which can be executed now.
    def getExec (self):
        insts = []
        for (index, inst) in enumerate(self.entries):

            # All Load instructions can be executed until we hit a store instruction in LSQ.
            # Store instruction can only be executed if it is at the head.
            if inst.isLoadInst() or (inst.isStoreInst() and index == 0):
                insts.append(inst)

            if inst.isStoreInst():
                break

        return insts
    


# Import functions data structures used by Out of Order Scheduler.
# from helpers import *


# Main scheduler class.
class oOOScheduler:


    def __init__ (self, infilename, outfilename):

        # Constant for this project.
        ARCHREGSCOUNT = 32

        # Parse input file. Open output file.
        self.input = self.parseInput(infilename)
        (self.numPhysReg, self.issueWidth) = next(self.input)
        self.outFile = open(outfilename, "w")

        # Various queues or latches connecting different pipeline stages.
        self.decodeQueue = pipelineStage(self.issueWidth)
        self.renameQueue = pipelineStage(self.issueWidth)
        self.dispatchQueue = pipelineStage(self.issueWidth)
        self.issueQueue = []
        self.reOrderBuffer = []
        self.lsq = loadStoreQueue()
        self.execQueue = []

        # Structures to track registers.
        self.mapTable = regMap(ARCHREGSCOUNT)
        self.freeList = freeList(self.numPhysReg)
        self.readyTable = readyQueue(self.numPhysReg)
        self.freeIngReg = []

        # Initially map R0->P0, R1->P1 and so on.
        for register in range(ARCHREGSCOUNT):
            self.mapTable.put(register, self.freeList.getFreeReg())

        # Instructions under consideraion so far.
        self.instructions = []

        # Start from cycle 0.
        self.cycle = 0

        # Track if we are currently fetching an instruction.
        # Used to detect when we have finished scheduling all instructions.
        self.fetching = True

        # Did any stage in the pipeline progress in last cycle?
        # Used to detect if pipeline is stuck because of bad scheduler design.
        self.hasProged = True


    #
    # Main scheduler functions
    #
    #
    def schedule (self):

        self.fetching = True
        self.hasProged = True

        while self.isSchedulingg() and self.hasProged:
            
            logging.info("Scheduling: %s" % self)
            
            self.hasProged = False

            # We process pipeline stages in opposite order to (try to) clear up
            # the subsequent stage before sending instruction forward from any
            # given stage.
            self.commit()
            self.writeback()
            self.issue()
            self.dispatch()
            self.rename()
            self.decode()
            self.fetch()
            for inst in (self.instructions[:]):
                if (inst.hasCommitted()) and (inst.overwritten != None):
                    self.freeList.free(inst.overwritten)
                    inst.overwritten = None
            # Move on to the next cycle.
            self.advanceCycle()


    def advanceCycle (self):
        for i in self.freeIngReg:
            self.freeList.free(i)
        self.freeIngReg = []

        self.cycle += 1

        logging.debug("Advanced scheduler to cycle # %d" % self.cycle)


    def madeProg (self):
        self.hasProged = True


    def isSchedulingg (self):
        return (
            self.fetching
            or any(not inst.hasCommitted() for inst in self.instructions)
        )


    #
    # Pipeline stages start here
    # #################################
    #

    #
    # Fetch Stage
    #
    def fetchIns (self):
        try:
    #run first if not error
            return next(self.input)
    #if error
        except StopIteration:
            self.fetching = False
            return None

    def fetch (self):
        fetched = 0
        while self.fetching and fetched < self.issueWidth:
            inst = self.fetchIns()
            if inst is not None:
                inst.fetchCycle = self.cycle
                self.instructions.append(inst)
                self.decodeQueue.pushIt(inst)

                fetched += 1

                self.madeProg()
                logging.debug("Fetched: %s" % inst)


    #
    # Decode Stage
    #
    def decode (self):
        while not self.decodeQueue.isEmpty():
            inst = self.decodeQueue.popIt()
            inst.decodeCycle = self.cycle
            self.renameQueue.pushIt(inst)
            self.madeProg()
            logging.debug("Decoded: %s" % inst)


    #
    # Rename Stage
    #
    def rename (self):
        while not self.renameQueue.isEmpty():
            inst = self.renameQueue.popIt()
            if self.freeList.isFree():
                inst.renameCycle= self.cycle

                if inst.inst == "I":
                    inst.srcReg1 = self.mapTable.get(inst.srcReg1) 
                    inst.overwritten = self.mapTable.get(inst.destReg)
                    phyDestReg = self.freeList.getFreeReg()
                    self.mapTable.put (inst.destReg, phyDestReg)
                    inst.destReg = phyDestReg

                elif inst.inst == "R":
                    inst.srcReg1 = self.mapTable.get(inst.srcReg1)
                    inst.srcReg2 = self.mapTable.get(inst.srcReg2) 
                    inst.overwritten = self.mapTable.get(inst.destReg)
                    phyDestReg = self.freeList.getFreeReg()
                    self.mapTable.put(inst.destReg, phyDestReg)
                    inst.destReg = phyDestReg
     			
                elif inst.inst == "L":
                    inst.srcReg1 = self.mapTable.get(inst.srcReg1)
                    inst.overwritten = self.mapTable.get(inst.destReg)
                    phyDestReg = self.freeList.getFreeReg()
                    self.mapTable.put (inst.destReg, phyDestReg)
                    inst.destReg = phyDestReg       		
            	
                elif inst.inst == "S":
                    inst.srcReg1 = self.mapTable.get(inst.srcReg1)
                    inst.srcReg2 = self.mapTable.get(inst.srcReg2) 	       			
                inst.renamed = True
                self.dispatchQueue.pushIt(inst)
                self.madeProg()
                logging.debug("Renamed: %s" % inst)
            
            elif inst.inst == "S":
                inst.renameCycle= self.cycle
                inst.srcReg1 = self.mapTable.get(inst.srcReg1)
                inst.srcReg2 = self.mapTable.get(inst.srcReg2)                     
                inst.renamed = True
                self.dispatchQueue.pushIt(inst)
                self.madeProg()
                logging.debug("Renamed: %s" % inst)                
            
            else:
                self.renameQueue.insertIt(inst)   
                break


    #
    # Dispatch Stage
    #
    def dispatch (self):
        while not self.dispatchQueue.isEmpty():
            inst = self.dispatchQueue.popIt()
            inst.dispatchCycle = self.cycle
            self.issueQueue.append(inst)
            self.reOrderBuffer.append(inst)

            if inst.isLoadStoreInst ():
                self.lsq.append(inst)
            if not inst.isStoreInst ():
                self.readyTable.clear(inst.destReg)
            self.madeProg()
            logging.debug("Dispatched: %s" % inst)


    #
    # Issue Stage
    #
    def issue (self):
        issued = 0
        for inst in list(self.issueQueue[:]):

            if len(self.execQueue) < self.issueWidth:
                if inst.inst == "I":
                    if self.is_inst_ready(inst):
                        inst.issueCycle = self.cycle
                        self.execQueue.append(inst)
                        self.issueQueue.remove(inst)
                        self.readyTable.clear(inst.destReg)
                    else:
                        continue

                if inst.inst == "R":
                    if self.is_inst_ready(inst):
                        inst.issueCycle = self.cycle
                        self.execQueue.append(inst)
                        self.issueQueue.remove(inst) 
                        self.readyTable.clear(inst.destReg)
                    else:
                        continue  

                if inst.inst == "L":
                    if self.is_inst_ready(inst):
                        inst.issueCycle = self.cycle
                        self.execQueue.append(inst)
                        self.issueQueue.remove(inst)
                        self.readyTable.clear(inst.destReg)
                    else:
                        continue  

                if inst.inst == "S":
                    if self.is_inst_ready(inst):
                        inst.issueCycle = self.cycle
                        self.execQueue.append(inst)
                        self.issueQueue.remove(inst)
                    else:
                        continue  

                self.madeProg()
                issued = issued + 1
                logging.debug("Issued: %s" % inst)
            else:
                break


    #
    # Writeback Stage
    #
    def writeback (self):
        for inst in self.execQueue[:]:
            if not inst.isLoadStoreInst():
                self.readyTable.ready(inst.destReg)
                self.execQueue.remove(inst)
                inst.writebackCycle = self.cycle
                self.madeProg()
                logging.debug("Writeback: %s" % inst)
            else:
                if self.lsq.canExecute(inst):
                    if inst.inst == "L":
                        self.readyTable.ready(inst.destReg)
                    self.lsq.remove(inst)
                    self.execQueue.remove(inst)
                    inst.writebackCycle = self.cycle
                    self.madeProg()
                    logging.debug("Writeback Load/Store: %s" % inst)


    #
    # Commit Stage
    #
    def commit (self):
        for inst in (self.reOrderBuffer[:]):
            if inst.hasWrittenback():
                inst.commitCycle = self.cycle
                self.reOrderBuffer.remove(inst)
                self.madeProg()
                logging.debug("Committed: %s" % inst)
            else:
                break

                

    def is_inst_ready (self, inst):

        if (not self.readyTable.isReady(inst.srcReg1)):
            return False
        
        if (inst.srcReg2 is not None) and (not self.readyTable.isReady(inst.srcReg2)):
            return False

        if inst.isLoadStoreInst():
            return self.lsq.canExecute(inst)

        return True

    #
    # File I/O functions
    # #################################
    #

    # Parse input file.
    def parseInput (self, infilename):

        
        try:
            with open(infilename, 'r') as file:
                
                # Regex strings to read field out of file line strings.
                config_parser = re.compile("^(\\d+),(\\d+)$")
                inst_parser = re.compile("^([RILS]),(\\d+),(\\d+),(\\d+)$")

                # Try to parse header
                header = file.readline()
                configs = config_parser.match(header)
                if configs:
                    (numPhyReg, issueWidth) = configs.group(1, 2)
                    numPhyReg = int(numPhyReg)
                    issueWidth = int(issueWidth)

                    if numPhyReg < 32:
                        print("Error: Invalid input file header: Number of "
                                "physical register is less than allowed minimum of %d" ,32)
                        sys.exit(1)

                    yield (numPhyReg, issueWidth)
                else:
                    print("Error: Invalid input file header!")
                    sys.exit(1)

                # Parse all remaining lines one by one.
                for (index, line) in enumerate(file):
                    configs = inst_parser.match(line)
                    if configs:
                        (Insts, op1, op2, op3) = configs.group(1, 2, 3, 4)

                        yield instruction(index, Insts, int(op1), int(op2), int(op3))
                    else:
                        print("Error: Invalid inst_set: %s" % (line))
                        sys.exit(1)

        except IOError:
            print("Error parsing input file!")
            sys.exit(1)


    def genOutFile (self):
        if self.isSchedulingg():
            self.outFile.write("")
            self.outFile.close()
            return

        for inst in self.instructions:
            self.outFile.write("%s,%s,%s,%s,%s,%s,%s\n" % (
                inst.fetchCycle,
                inst.decodeCycle,
                inst.renameCycle,
                inst.dispatchCycle,
                inst.issueCycle,
                inst.writebackCycle,
                inst.commitCycle,
            ))

        self.outFile.close()

    def __str__ (self):
        return "[oOOScheduler cycle=%d]" % (self.cycle)
        






# Main function
def main (args):

    # Parse command line arguments
    if len(args) != 3:
        print ("Error!")
      
        sys.exit(1)

    infilename = args[1]
    outfilename = args[2]

    # Setup logging.
    # logging.basicConfig(level=logging.INFO, format='[%(filename)18s:%(lineno)-4d] %(levelname)-5s:  %(message)s')

    # Uncomment the following line to print debug messages to STDOUT.
    # logging.getLogger().setLevel(logging.DEBUG)

    # Fire up the scheduler.
    ooo = oOOScheduler(infilename, outfilename)
    ooo.schedule()
    ooo.genOutFile()


if __name__ == "__main__":
    main(sys.argv)