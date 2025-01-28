# railway_classes.py


from datetime import timedelta

from lxml import etree


IdMap={}

class StopSpec:
    def __init__(self, id, dwell,arrival,departure):
        self.id=id
        self.dwell=dwell
        self.arrival=arrival
        self.departure=departure

class Course:
    allCourses={}
    coursesByName={}
    def __init__(self, id,name,entranceTime,exitTime):
        self.name=name
        self.id=id
        self.entranceTime=entranceTime
        self.exitTime=exitTime
        self.stops=[]
        Course.allCourses[id]=self
        Course.coursesByName[name] = self

    def addStop(self,sid,dwell,arrival,departure):
        self.stops.append(StopSpec(sid,dwell,arrival,departure))


class Visualization:
    def __init__(self, start_x, start_y, end_x, end_y):
        self.start = (start_x, start_y)
        self.end = (end_x, end_y)

    def __repr__(self):
        return f"Visualization(start={self.start}, end={self.end})"


class TopologyPart:
    def __init__(self, topoPart_Id, length, speednormal, speedinverse, gradient, curve, visualization=None):
        self.topoPart_Id = topoPart_Id
        self.length = length
        self.speednormal = speednormal
        self.speedinverse = speedinverse
        self.gradient = gradient
        self.curve = curve
        self.visualization = visualization  # Visualization instance

    def __repr__(self):
        return f"TopologyPart({self.topoPart_Id}, {self.length}, {self.speednormal}, {self.speedinverse}, {self.gradient}, {self.curve}, {self.visualization})"
    def __eq__(self, other):
        if isinstance(other, TopologyPart):
            return (self.topoPart_Id == other.topoPart_Id and
                    self.length == other.length and
                    self.speednormal == other.speednormal and
                    self.speedinverse == other.speedinverse and
                    self.gradient == other.gradient and
                    self.curve == other.curve)
        return False

    def __hash__(self):
        return hash((self.topoPart_Id, self.length, self.speednormal, self.speedinverse, self.gradient, self.curve))
    
class TopologySequence:
    def __init__(self, topoSeq_Id):
        self.topoSeq_Id = topoSeq_Id
        self.topo_part_refs = []  # List of reference IDs for topology parts
        self.direction = None  # To store direction (1 for forward, -1 for backward)

    def add_topo_part_ref(self, topoPart_RefId, direction):
        self.topo_part_refs.append((topoPart_RefId, direction))

    def __repr__(self):
        return f"TopologySequence({self.topoSeq_Id}, {self.topo_part_refs})"
    
    def __eq__(self, other):
        if isinstance(other, TopologySequence):
            return self.topoSeq_Id == other.topoSeq_Id
        return False
    
    def __hash__(self):
        return hash(self.topoSeq_Id)

class ITTrackCircuit:
    allITTC = {}

    def __init__(self,name):
        self.name = name
        self.joints = []
        self.topology_parts = []
        self.topology_sequences= []
        ITTrackCircuit.allITTC[name] = self

    def __repr__(self):
        return "ITrackCircuit(" + self.name + ","+str(self.joints)+")\r\n"
    
    def addJoint(self,jid):
        if(jid!="00000000-0000-0000-0000-000000000000"):
            if jid not in self.joints:
                self.joints.append(jid)

    def add_topology_part(self, topo_part):
        if topo_part not in self.topology_parts:
            self.topology_parts.append(topo_part)
        else:
            print(f"Duplicate TopologyPart  ignored.")

    def add_topology_sequence(self, topo_sequence):
        if topo_sequence not in self.topology_sequences:
            self.topology_sequences.append(topo_sequence)
        else:
            print(f"Duplicate TopologySequence ignored for {self.name}.")

    @staticmethod
    def getOrCreate(name):
        if name in ITTrackCircuit.allITTC:
            return ITTrackCircuit.allITTC[name]
        else:
            return ITTrackCircuit(name)


class ITSignal:
    allSignals={}
    virtual_creation_count = 0

    def __init__(self, name, id, aspects, visibilityDistance=0):
        self.name = name
        self.id = id
        self.aspects = aspects
        self.visibilityDistance = visibilityDistance
        IdMap[id] = self
        ITSignal.allSignals[id] = self

    def __repr__(self):
        return f"Signal({self.name}, {self.aspects}, visibilityDistance={self.visibilityDistance})\r\n"

    def getOrCreate(name, id, aspects, visibilityDistance=0):
        
        for signal in ITSignal.allSignals.values():
            if signal.name == name:
                print(f"Found existing signal: {name}")
                return signal
        
        print(f"Created new signal: {name}")
        return ITSignal(name, id, aspects,visibilityDistance)
  
    def getNbAspects(self):
        return self.aspects

class Block:
    allBlocks = {}
    blocksByTdsList = {}

    def __init__(self, ensig, exsig, tdslist, id, name, topoSeqRefs=None, formationTime=0, releaseTime=0):
        self.ensig = ensig
        self.exsig = exsig
        self.tdslist = tdslist[:]
        self.topoSeqRefs = topoSeqRefs[:] if topoSeqRefs is not None else []
        self.name = name
        self.id = id
        self.formationTime = formationTime
        self.releaseTime = releaseTime

        Block.allBlocks[id] = self
        Block.blocksByTdsList[Block.getSigTdsTuple(ensig, exsig, tdslist)] = self

    @staticmethod
    def getSigTdsTuple(ensig, exsig, tdslist):
        sigtdslist = []
        sigtdslist.append(ensig)
        sigtdslist.append(exsig)
        sigtdslist.extend(tdslist)
        return tuple(sigtdslist)

    @staticmethod
    def isBlockBySignals(ensig, exsig):
        for block in Block.blocksByTdsList.values():
            if block.ensig == ensig and block.exsig == exsig:
                return True
        return False

    @staticmethod
    def isBlock(ensig, exsig, tdslist):
        if Block.getSigTdsTuple(ensig, exsig, tdslist) in Block.blocksByTdsList:
            return True
        else:
            return False

    @staticmethod
    def getBlock(ensig, exsig, tdslist):
        return Block.blocksByTdsList[Block.getSigTdsTuple(ensig, exsig, tdslist)]

    @staticmethod
    def getOrCreate(ensig, exsig, tdslist, blockid, blockname, topoSeqRefs=None, formationTime=0, releaseTime=0):
        return Block(ensig, exsig, tdslist, blockid, blockname, topoSeqRefs, formationTime, releaseTime)

    @staticmethod
    def getBlocksByName(name):
        blocks = []
        for block in Block.allBlocks.values():
            if name in block.name:
                blocks.append(block)
        return blocks

    def __repr__(self):
        return f"Block({self.name} {str(self.tdslist)}, formationTime={self.formationTime}, releaseTime={self.releaseTime})\r\n"

    def getTDSList(self):
        return self.tdslist
    
    def getsequencelist(self):
        return self.topoSeqRefs


class StoppingPointGroup:
    allStoppingPointGroups={}
    def __init__(self, id,name):
        self.id=id
        self.name=name
        self.spids=[]
        StoppingPointGroup.allStoppingPointGroups[id]=self

    def addStoppingPoint(self,spid):
        if spid not in self.spids:
            self.spids.append(spid)

    def __repr__(self):
        return "StoppingPointGroup(" + self.name + " "+ str(len(self.spids))+ ")\r\n"

class ITStoppingPoint:
    allStoppingPoints={}
    def __init__(self,name,id, maximumTrainLength = 0,sp_type='Platform'):
        valid_types = ['Platform', 'Siding', 'Other']
        if sp_type not in valid_types:
            raise ValueError(f"Invalid stopping point type: {sp_type}")
        if not isinstance(maximumTrainLength, (int, float)) or maximumTrainLength < 0:
            raise ValueError(f"Invalid maximum train length: {maximumTrainLength}, it must be a positive number")
        self.name=name
        self.id=id
        self.maximumTrainLength = maximumTrainLength
        self.tdss=[]
        self.sigs=[]
        IdMap[id]=self
        self.type = sp_type
        ITStoppingPoint.allStoppingPoints[id]=self
              
    def __repr__(self):
        return f"StoppingPoint({self.name}, maxTrainLength={self.maximumTrainLength})\r\n"

    def addSig(self,sig):
        if sig not in self.sigs:
            self.sigs.append(sig)

    def addTds(self, tds):
        if tds not in self.tdss:
        	self.tdss.append(tds) 
    
 

class JITDSDetail:
    def __init__(self, tds, run, clear, stopid, occupied_tds=None):
        self.tds = tds
        self.run = run
        self.clear = clear
        self.stopid = stopid
        self.occupied_tds = occupied_tds if occupied_tds else []

    def __repr__(self):
        return f"JITDSDetail({self.tds} {self.run} {self.clear} {self.stopid} {self.occupied_tds})\n"


class Journey:
    allJourneys = {}

    def __init__(self, name):
        self.blockSequence = []
        self.journeyInstances = []  
        self.name = name
        Journey.allJourneys[self.name] = self

    def addBlockRef(self, blockid):
        self.blockSequence.append(blockid)

    def addJourneyInstance(self, journey_instance):
        self.journeyInstances.append(journey_instance)  

    def getBlockSequence(self):
        return tuple(self.blockSequence)

    def __repr__(self):
        return "Journey(" + self.name + " " + str(self.blockSequence) + " " + str(self.journeyInstances) + ")\r\n"
    


    
class JourneyInstance:
    def __init__(self, journey,rolling_stock_name = None, tdsDetails=None):
        self.journey = journey  
        self.rolling_stock_name =rolling_stock_name
        # Initialize tdsDetails to an empty list if None is provided
        self.JITDSDetail = tdsDetails if tdsDetails is not None else []  
        self.journey.addJourneyInstance(self)   

    def addJITDSDetail(self, tdsDet):
        self.JITDSDetail.append(tdsDet)  
        print("Detail added to journey instance:", tdsDet)

    def getStopsId(self):
        stops = []
        for det in self.JITDSDetail:
            if det.stopid != "":
                stops.append(det.stopid)
        return stops
    
    def getBlockSequence(self):
        return self.journey.getBlockSequence()
    
    def getRollingStockName(self):
        return self.rolling_stock_name

    def __repr__(self):
        return "JourneyInstance(" + str(self.JITDSDetail) + ")\r\n"
    



    



    








#Time Related functions


def sec_to_hhmmss(time_sec):
    import time
    return time.strftime('%H:%M:%S',time.gmtime(time_sec))

def get_sec(time_str):
    sp=time_str.split(" ")
    d=0
    hms = time_str

    if(len(sp)==2):
        d=sp[0]
        hms=sp[1]

    h, m, s = hms.split(':')
    return int(d)*86400+int(h) * 3600 + int(m) * 60 + int(round(float(s)))

def prettify(element):
    rough_string = etree.tostring(element, pretty_print=True, encoding='UTF-8')
    reparsed = etree.fromstring(rough_string)
    return etree.tostring(reparsed, pretty_print=True, encoding='unicode')

def seconds_to_hhmmss(seconds):
    return str(timedelta(seconds=seconds))

def hhmmss_to_seconds(hhmmss):
    
    # Clean up input and remove leading/trailing spaces
    hhmmss = hhmmss.strip()

    # Check if there is a day component (e.g., '0 00:14:00')
    if ' ' in hhmmss:
        day_part, time_part = hhmmss.split(' ', 1)  # Split at the space
    else:
        day_part, time_part = '0', hhmmss  # No day part, default to '0'

    # Now handle the time part (e.g., '00:14:00')
    time_parts = time_part.split(':')
    
    # Handle cases where parts are missing by prepending '0'
    while len(time_parts) < 3:
        time_parts.insert(0, '0')

    # Convert day part to seconds (24 hours per day)
    try:
        day_seconds = int(day_part) * 86400  # 1 day = 86400 seconds
        time_parts = list(map(int, time_parts))
        return day_seconds + (time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2])
    except ValueError as e:
        print(f"Error converting time '{hhmmss}': {e}")
        raise



def hhmmss_to_second_two(hhmmss):
    # Clean up the input and check if it's valid
    hhmmss = hhmmss.strip()  # Remove any leading or trailing spaces
    if hhmmss == "":
        raise ValueError("Time string is empty or invalid")
    
    time_parts = list(map(int, hhmmss.replace(' ', '').split(':')))
    
    # Ensure there are exactly three time components
    if len(time_parts) != 3:
        raise ValueError(f"Invalid time format: {hhmmss}")
    
    return time_parts[0] * 3600 + time_parts[1] * 60 + time_parts[2]