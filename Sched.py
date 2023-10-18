class Instruction:
    allinstructions = []
    
    def __init__(self, insNumber, ins, r1, r2, r3) :
        self.insNumber = insNumber
        self.ins = ins
        
        if ins == "I":
            self.sourceReg1 = r2
            self.sourceReg2 = None
            self.destReg = r1
            self.immediate = r3
            self.memAccess = False
        elif ins == "R":
            self.sourceReg1 = r2
            self.sourceReg2 = r3
            self.destReg = r1
            self.immediate = None
            self.memAccess = False
        elif ins == "L":
            self.sourceReg1 = r3
            self.sourceReg2 = None
            self.destReg = r1
            self.immediate = r2
            self.memAccess = True
        elif ins == "S":
            self.sourceReg1 = r1
            self.sourceReg2 = r3
            self.destReg = None
            self.immediate = r2
            self.memAccess = True
        
        self.overwritten = False
        self.renamed = False
        self.fetchCycle = None
        self.decodeCycle = None
        self.renameCycle = None
        self.dispatchCycle = None
        self.issueCycle = None
        self.commitCycle = None
        self.writtenBack = True
        self.has_commited = True
        Instruction.allinstructions.append(self)
        
        # print(ins,self.destReg,self.sourceReg1,self.sourceReg2)

def isLoadStoreIns(ins):
    if ins.ins == "L" or ins.ins == "S":
        return True
    
    else:
        return False
            
def isInsReady(ins):
    if(not readyTable[ins.sourceReg1]):
        return False
    if(ins.sourceReg2 is not None) and (not readyTable[ins.sourceReg1]):
        return False
    if (ins.ins == "S") or (ins.ins == "L"):
        count=0
        for i in loadStoreQueue:
            if (ins.ins == "L") or (ins.ins == "S" and count==0):
                count+=1
                if i == ins:
                    return True
            if ins.ins == "S":
                break
        return False                                

def schedule(ins):
        global currentCycle
        fetching = True
        has_progressed = True
        
        while ins is not None:
            
            # logging.info("Scheduling: %s" % 
            # print(currentCycle)
            # has_progressed = False
            # We process pipeline stages in opposite order to (try to) clear up
            # the subsequent stage before sending instruction forward from any
            # given stage.
            # print(1)
            commit()
            # print(1)
            writeBack()
            # print(1)
            issue()
            # print(1)
            dispatch()
            # print(1)
            rename()
            # print(1)
            decode()
            # print(1)
            fetch(ins)
            # print(1)
            # for inst in Instruction.allinstructions:
            #     if (inst.overwritten != None):
            #         print(inst.overwritten);
            #         freeList.get_nowait(inst.overwritten)
            #         inst.overwritten = None
            # print(advanceCycle())
def advanceCycle():
    for i in freeingRegisters:
        freeList.append(i)
        # print("advanceCycle")
        currentCycle = currentCycle + 1
        return currentCycle
        
def parseFirstLine (firstLine):
    info = re.compile("^(\\d+),(\\d+)$")
    impInfo = info.match(firstLine)
    if not impInfo:
        print("invalid first line")
        SystemExit()
    # using regex to get the first line with number of physical registers and issue width for the rest of the program
    else:
        numPhysicalReg,issueWidth = map(int,impInfo.group(1,2))
        if numPhysicalReg < 32:
            print("error, cant proceed because of the constraints mentioned in the assignment")
            SystemExit()
        
        return numPhysicalReg, issueWidth
    
# def parserest():

def fetchInst(ins):
    return ins
    
def fetch(inst) :
    global currentCycle
    fetched = 0
    # cycle.put(0)
    # index = cycle.get()
    while fetched < issueWidth:
        #fetch the instruction and put it in inst=
        # ins = fetchInst()
        ins = inst
        if ins is not None:
            fetchCycle = currentCycle
            fetchQueue.put_nowait(ins)
            decodeQueue.put_nowait(ins)
            fetched += 1
            print("fetched",ins)

        # break;
            # print(currentCycle)
        # currentCycle.append(index)
        # cycle.put(index)
        
    
        
        
            
    # print()
def decode():
    # print(decodeQueue.get_nowait())
    
    while decodeQueue.empty() is False:
        # print("decode")
        # index = cycle.get()
        # index+=1
        global currentCycle
        currentCycle = currentCycle + 1
        
        print("decode",currentCycle)
        # decodeCycle = currentCycle +1
        inst  = decodeQueue.get_nowait()
        renameQueue.put_nowait(inst)
        # currentCycle.append(index)
    print()
def rename():
    while renameQueue.empty() is False:
        # print("rename")
        ins = renameQueue.get_nowait()
        if freeList.empty() is False:#check if free list has free registers
            # renameCycle = currentCycle+1
            # currentCycle = currentCycle + 1
            print(currentCycle)
            if ins.ins == "I":
                ins.sourceReg1 = mapTable[ins.sourceReg1]
                ins.overwritten = mapTable[ins.destReg]
                physicalDestReg = freeList.get_nowait()
                mapTable[ins.destReg] = physicalDestReg
                ins.destReg = physicalDestReg
            elif ins.ins == "R":
                ins.sourceReg1 = mapTable[ins.sourceReg1]
                ins.sourceReg2 = mapTable[ins.sourceReg2]
                ins.overwritten = mapTable[ins.destReg]
                physicalDestReg = freeList.get_nowait()
                mapTable[ins.destReg] = physicalDestReg
                ins.destReg = physicalDestReg
            
            elif ins.ins == "L":
                ins.sourceReg1 = mapTable[ins.sourceReg1]
                ins.overwritten = mapTable[ins.destReg]
                physicalDestReg = freeList.get_nowait()
                mapTable[ins.destReg] = physicalDestReg
                ins.destReg = physicalDestReg
            elif ins.ins == "S":
                ins.sourceReg1 = mapTable[ins.sourceReg1]
                ins.sourceReg2 = mapTable[ins.sourceReg2]
            ins.renameCycle = True
            dispatchQueue.put_nowait(ins)
        elif ins.ins == "S":
            renameCycle = currentCycle+1
            ins.sorceReg1 = mapTable[ins.sourceReg1]
            ins.sourceReg2 =mapTable[ins.sourceReg2]
                    
            ins.renameCycle = True   
            dispatchQueue.put_nowait(ins)     
            currentCycle+=1
            print(currentCycle)        
        
        else:
            print("shit is happening")
                
                
    # print()
def dispatch():
    # print("dispatch")
    while dispatchQueue.empty() is False:
        ins = dispatchQueue.get_nowait()
        # dispatchCycle = currentCycle + 1
        # currentCycle = currentCycle + 1
        print(currentCycle)
        issueQueue.append(ins)
        reOrderBuffer.put_nowait(ins)
        if ((ins.ins == "S" ) or (ins.ins == "L")):
            loadStoreQueue.put_nowait(ins)
        if (ins.ins != "S"):
            readyTable[ins.destReg] = False
    #  print()
def issue():
        issued = 0
        # print("issue")
        for ins in issueQueue:
            if len(executingQueue) < issueWidth:
                # currentCycle = currentCycle + 1

                print(currentCycle)
                if ins.ins == "I":
                    if isInsReady(ins):
                        # ins.issue_cycle = cycle
                        executingQueue.append(ins)
                        issueQueue.remove(ins)
                        readyTable.clear(ins.dstReg)
                    else:
                        continue
                if ins.ins == "R":
                    if isInsReady(ins):
                        # ins.issue_cycle = cycle
                        executingQueue.append(ins)
                        issueQueue.remove(ins) 
                        readyTable.clear(ins.dstReg)
                    else:
                        continue  
                if ins.ins == "L":
                    if isInsReady(ins):
                        # ins.issue_cycle = cycle
                        executingQueue.append(ins)
                        issueQueue.remove(ins)
                        readyTable.clear(ins.dstReg)
                    else:
                        continue  
                if ins.ins == "S":
                    if isInsReady(ins):
                        # ins.issue_cycle = cycle
                        executingQueue.append(ins)
                        issueQueue.remove(ins)
                    else:
                        continue  
                # made_progress()
                issued = issued + 1
                # logging.debug("Issued: %s" % ins)
            else:
                break
        

def writeBack():
        #   print("wb")
        for ins in executingQueue:
                # currentCycle = currentCycle + 1

                print(currentCycle)
                if not ins.isLoadStoreInst():
                    readyTable[ins.destReg] = True
                    executingQueue.pop(ins)
                    # ins.writebackcycle = cycle
                    # madeprogress()
                    # logging.debug("Writeback: %s" % ins)
                else:
                    if loadStoreQueue.canexecute(ins):
                        if ins.ins == "L":
                            readyTable[ins.destReg] = True

                        loadStoreQueue.get_nowait(ins)
                        executingQueue.pop(ins)
                        # ins.writebackcycle = cycle
                        # madeprogress()
                        # logging.debug("Writeback Load/Store: %s" % ins)
        #  print()

def commit():
        #  print("commit")
        if reOrderBuffer.empty() is False:
            for inst in range(256):
                    # currentCycle = currentCycle + 1

                    print(currentCycle)
                    ins = reOrderBuffer.get()
                    if ins.writtenBack is not None:
                        # ns.commit_cycle = self.cycle
                        reOrderBuffer.get_nowait(ins)
                        # self.made_progress()
                        # logging.debug("Committed: %s" % ins)
                    else:
                        break
            # print()




import re   
import csv
from queue import Queue
index =0
with open("python_projects\comp_arch_ooo\ex1.txt","r") as f:
    firstLine = f.readline()
    numPhysicalReg, issueWidth =  parseFirstLine(firstLine)  
    rest = csv.reader(f,delimiter=",")
    for row in rest:
            # print(index,row[0],int(row[1]),int(row[2]),int(row[3]))
            Instruction(index, row[0],int(row[1]),int(row[2]),int(row[3]))
            index+=1
            
            
# print(dir(Instruction))            
    
print(numPhysicalReg, issueWidth)
currentCycle = 0
fetchQueue = Queue(maxsize = 256)
decodeQueue = Queue(maxsize = 256)
renameQueue = Queue(maxsize = 256)
readyTable = []
mapTable = []
freeList = Queue(maxsize=256)
issueQueue = []
dispatchQueue = Queue(maxsize = 256)
writebackQueue = Queue(maxsize = 256)
reOrderBuffer = Queue(maxsize=256)
commitQueue = Queue(maxsize = 256)
loadStoreQueue = Queue(maxsize=256)
executingQueue=[]
freeingRegisters = []
# cycle = Queue()
# cycle.put(0)
# try:
    # for i in cycle.iter():
    #     print(i)
    # for ins in Instruction.allinstructions:
    #     schedule(ins)
        
    # print(currentCycle)
# except:
#     print("fuck")
# writeBack()
# issue()
# dispatch()
# rename()
# decode()
# fetch()
# for i in cycle.iter():
#         print(i)
for ins in Instruction.allinstructions:
        schedule(ins)
        

            




'''map table = array
    free list = queue
    ready table = array of bool for physical registers, which are defined in the 1st line
    issue queue = dictionary
    Reorder buffer = queue
    fetch = queue, sends n instructions at a time
    decode = queue same thing get the instructoin send them in fifo
    rename = same as above, stall only here in case we run out of rename registers
    dispatch = queue, same as above
    from dispatch it goes to issue queue
    '''
        
        

