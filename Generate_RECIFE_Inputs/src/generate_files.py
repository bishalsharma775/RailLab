
# #I am using this testing on the same code to do a few Things:
#     Change the name of the journey by the name of the blocksections making it[done]
#     Always make sure if the journey instance is part of a journey than give name _First_Jounrney_Instance at the end of the Jouney
#     If the two journey instance are part of a journey then make sure you add them inside that journey and give them seperate names
#     Test again and see if you get the similar results

from lxml import etree
from statistics import mean
import sqlite3
from xml.dom import minidom
from datetime import timedelta
import json
from datetime import datetime
import argparse
import random
import os




from railway_classes import (
    StopSpec, Course, TopologyPart, ITTrackCircuit, ITSignal, Block, 
    StoppingPointGroup, ITStoppingPoint, JITDSDetail, Journey,JourneyInstance,Visualization,TopologyPart,TopologySequence,
    seconds_to_hhmmss, get_sec, prettify, sec_to_hhmmss, hhmmss_to_seconds
)




def saveRS(path, inf_id, vehicles, rolling_stock_details):
    root = etree.Element('recifeObjects')
    inf = etree.SubElement(root, 'rollingStocksDefinition')
    inf.set("rollingStocksDefinition_Id", inf_id)
    etree.SubElement(inf, 'name').text = inf_id
    etree.SubElement(inf, 'description').text = "Generated with IngeTime2Recife python script (GML)"

    vts = etree.SubElement(inf, 'vehicleTypes')
    for rolling_stocks in rolling_stock_details:
        vt = etree.SubElement(vts, 'vehicleType')
        vt.set('vehiculeType_Id', rolling_stocks['Guid']) 

        total_mass = 0.0
        total_length = 0.0
        combined_names = [] 
        

        for rolling_stock in rolling_stocks['Vehicles']:
            for vehicle in vehicles:
                if vehicle['Guid'] == rolling_stock['Guid']:
                    # print("found")
                    total_mass += vehicle['MassTons']
                    total_length += vehicle['LengthMeters']
                    combined_names.append(vehicle['Name'])
                    
       
        etree.SubElement(vt, "name").text = ', '.join(combined_names)  
        etree.SubElement(vt, "length").text = str(int(total_length))
        etree.SubElement(vt, "rotationMassFactor").text = str(1.06)  
        etree.SubElement(vt, "mass").text = str(int(total_mass))
       

        if 'Efforts' in rolling_stocks and 'CL' in rolling_stocks['Efforts'] and '22,5' in rolling_stocks['Efforts']['CL']:
            tractive_effort_curve = etree.SubElement(vt, 'tractiveEffortCurve')
            for speed, effort in rolling_stocks['Efforts']['CL']['22,5']:
                tractive_effort = etree.SubElement(tractive_effort_curve, 'tractiveEffort')
                etree.SubElement(tractive_effort, 'atSpeed').text = str(speed)
                etree.SubElement(tractive_effort, 'effortValue').text = str(effort)

    rss = etree.SubElement(inf, 'rollingStocks')
    for rolling_stock in rolling_stock_details:
        rs = etree.SubElement(rss, 'rollingStock')
        rs.set('rollingStock_Id', rolling_stock['Guid'])
        vehicle_type_sequence = etree.SubElement(rs, 'vehicleTypeSequence')
        vehicle_type_ref = etree.SubElement(vehicle_type_sequence, 'vehicleType_RefId')
        vehicle_type_ref.text = rolling_stock['Guid']
        braking_curve = etree.SubElement(rs, 'brakingCurve')
        deceleration = etree.SubElement(braking_curve, 'deceleration')
        etree.SubElement(deceleration, 'fromSpeed').text = '500'  
        etree.SubElement(deceleration, 'toSpeed').text = '0'      
        etree.SubElement(deceleration, 'accelerationValue').text = str(-rolling_stock['Deceleration'])

        resistance_factors = etree.SubElement(rs, 'resistanceFactors')
        etree.SubElement(resistance_factors, 'A').text = str(rolling_stock['CoefficientA'])
        etree.SubElement(resistance_factors, 'B').text = str(rolling_stock['CoefficientB'])
        etree.SubElement(resistance_factors, 'C').text = str(rolling_stock['CoefficientC'])

    tree = etree.ElementTree(root)
    tree.write(path, pretty_print=True, xml_declaration=True, encoding="utf-8")


def read_vehicle_details_from_xml(xml_string):
    root = etree.parse(xml_string)
    vehicle_details = []

    for vehicle in root.findall('.//VehicleXml'):
        vehicle_detail = {
            'Guid': vehicle.find('Guid').text,
            'Name': vehicle.find('Name').text,
            'LengthMeters': float(vehicle.find('LengthMeters').text),
            'CoefficientIMT': float(vehicle.find('CoefficientIMT').text),
            'MassTons': float(vehicle.find('MassTons').text),
            'MaximumSpeedKmph': float(vehicle.find('MaximumSpeedKmph').text),
            'CoefficientA': float(vehicle.find('CoefficientA').text),
            'CoefficientB': float(vehicle.find('CoefficientB').text),
            'CoefficientC': float(vehicle.find('CoefficientC').text),
            'CoefficientCTunnelDuctsClosed': float(vehicle.find('CoefficientCTunnelDuctsClosed').text),
            'CoefficientCTunnelDuctsOpen': float(vehicle.find('CoefficientCTunnelDuctsOpen').text),
            'PowerStaticWatts': float(vehicle.find('PowerStaticWatts').text)
        }
        vehicle_details.append(vehicle_detail)

    return vehicle_details

def read_rolling_stock_details_from_xml(xml_string):
    root = etree.parse(xml_string)
    
    rolling_stock_details = []
    
    for train_set in root.findall('.//TrainSetTemplateXml'):
        train_details = {
            'Guid': train_set.find('Guid').text,
            'CoefficientA': float(train_set.find('CoefficientA').text),
            'CoefficientB': float(train_set.find('CoefficientB').text),
            'CoefficientC': float(train_set.find('CoefficientC').text),
            'ComfortAcceleration': float(train_set.find('ComfortAcceleration').text),
            'Deceleration': float(train_set.find('Deceleration').text),
            'Name': train_set.find('Name').text,
            'MaximumEffort': float(train_set.find('MaximumEffort/Newton').text),
            'EnergyEfficiency': float(train_set.find('EnergyEffciency').text),
            'Vehicles': [],
            'Efforts': {}
        }

 
        for effort in train_set.findall('Efforts/TractiveEffortCurvePointXml'):
            comfort_level = effort.find('Comfort').text
            speed = float(effort.find('Speed/KilometerPerHour').text)
            effort_value = float(effort.find('Effort/Newton').text)
            electric_level = effort.find('ElectricProfilAndRestriction').text
            
    
            if comfort_level not in train_details['Efforts']:
                train_details['Efforts'][comfort_level] = {}
            if electric_level not in train_details['Efforts'][comfort_level]:
                train_details['Efforts'][comfort_level][electric_level] = []

         
            train_details['Efforts'][comfort_level][electric_level].append((speed, effort_value))
        
     
        for vehicle in train_set.findall('Vehicles/ValueTupleOfGuidInt32'):
            vehicle_details = {
                'Guid': vehicle.find('Item1').text,
                'Quantity': int(vehicle.find('Item2').text)
            }
            train_details['Vehicles'].append(vehicle_details)
        
        rolling_stock_details.append(train_details)
    
    return rolling_stock_details



def saveInfra(path,inf_id):
    root = etree.Element('recifeObjects')
    inf = etree.SubElement(root,'InfrastructureDefinition')
    inf.set("infrastructure_id",inf_id)
    etree.SubElement(inf,'name').text=inf_id
    etree.SubElement(inf,'description').text="Generated with IngeTime2Recife python script (GML) "

    # Create trackDetectionSections element
    tdsroot = etree.SubElement(inf, 'trackDetectionSections')
    for tds_name, tds in ITTrackCircuit.allITTC.items():
        # print("here come the tdsssssssssss", tds)
        te = etree.SubElement(tdsroot, 'trackDetectionSection')
        te.set("TDS_Id", tds_name)
        etree.SubElement(te, 'name').text = tds_name
        topo = etree.SubElement(te, 'topologyParts')
        for part in tds.topology_parts:
            topo_part = etree.SubElement(topo,'topologyPart')
            topo_part.set("topoPart_Id", part.topoPart_Id)
            etree.SubElement(topo_part, 'length').text = str(part.length)
            etree.SubElement(topo_part, 'speednormal').text = str(part.speednormal)
            etree.SubElement(topo_part, 'speedinverse').text = str(part.speedinverse)
            etree.SubElement(topo_part, 'gradient').text = str(part.gradient)
            etree.SubElement(topo_part, 'curve').text = str(part.curve)
        
            if part.visualization:
                vis = etree.SubElement(topo_part, 'visualization')
                start = etree.SubElement(vis, 'start')
                start.set("x", str(part.visualization.start[0]))
                start.set("y", str(part.visualization.start[1]))
                end = etree.SubElement(vis, 'end')
                end.set("x", str(part.visualization.end[0]))
                end.set("y", str(part.visualization.end[1]))
        
        topo_seq_root = etree.SubElement(te, 'topologySequences')
        for seq in tds.topology_sequences:
            topo_seq = etree.SubElement(topo_seq_root, 'topologySequence')
            topo_seq.set("topoSeq_Id", seq.topoSeq_Id)
            topo_part_list = etree.SubElement(topo_seq, 'topoPart_List')

            for ref_id, direction in seq.topo_part_refs:
                topo_part_seq_elmt = etree.SubElement(topo_part_list, 'topoPartSeqElmt')
                topo_part_ref = etree.SubElement(topo_part_seq_elmt, 'topoPart_RefId')
                topo_part_ref.set("direction", str(direction))  # Add direction (1 or -1)
                topo_part_ref.text = ref_id
 

    signal_count = 0
    sigroot=etree.SubElement(inf,'signals')
    for sig in ITSignal.allSignals:
        si=etree.SubElement(sigroot,'signal')
        signal_name = ITSignal.allSignals[sig].name
        si.set('signal_Id', signal_name)
        etree.SubElement(si,'name').text=ITSignal.allSignals[sig].name
        etree.SubElement(si,'aspects').text=str(ITSignal.allSignals[sig].getNbAspects())
        etree.SubElement(si,'visibilityDistance').text=str(ITSignal.allSignals[sig].visibilityDistance)
        signal_count += 1
    # print("Total signals created:", signal_count)
    blockroot=etree.SubElement(inf,'blocks')
    for name in Block.allBlocks:
        block=Block.allBlocks[name]
        bl=etree.SubElement(blockroot,'block')
        bl.set('block_Id',block.id)
        etree.SubElement(bl,'name').text=block.name
        etree.SubElement(bl,'entrySignal_RefId').text=block.ensig
        etree.SubElement(bl,'exitSignal_RefId').text=block.exsig
        etree.SubElement(bl,'formationTime').text=str(block.formationTime)
        etree.SubElement(bl,'releaseTime').text=str(block.releaseTime)
        top=etree.SubElement(bl,'TDS_Topology_List')
        tdslist=block.getTDSList()
        idx=0
        for tds in tdslist:
            t=etree.SubElement(top,'TDS_Topology')
            t.set('index',str(idx))
            etree.SubElement(t,'TDS_RefId').text=tds
            idx+=1
            
            
    
    sproot=etree.SubElement(inf,'stoppingPoints')
    for spid in ITStoppingPoint.allStoppingPoints:
        spe=etree.SubElement(sproot, 'stoppingPoint')
        spe.set('stoPo_Id',spid)
        etree.SubElement(spe, 'name').text=ITStoppingPoint.allStoppingPoints[spid].name
        etree.SubElement(spe, 'type').text =ITStoppingPoint.allStoppingPoints[spid].type
        etree.SubElement(spe, 'maximumTrainLength').text =str(ITStoppingPoint.allStoppingPoints[spid].maximumTrainLength)
        slist=etree.SubElement(spe, 'signals_List')
        for sig in ITStoppingPoint.allStoppingPoints[spid].sigs:
            etree.SubElement(slist, 'signal_RefId').text = sig
        tlist=etree.SubElement(spe, 'TDSections')
        for tds in ITStoppingPoint.allStoppingPoints[spid].tdss:
            etree.SubElement(tlist, 'TDS_RefId').text = tds

    spgroot=etree.SubElement(inf,'stoppingPointsGroups')
    for spgid in StoppingPointGroup.allStoppingPointGroups:
        spg=etree.SubElement(spgroot,'stoppingPointsGroup')
        spg.set('stoGro_Id',spgid)
        etree.SubElement(spg,'name').text=StoppingPointGroup.allStoppingPointGroups[spgid].name
        etree.SubElement(spg,'priorityFactor').text="1"
        spl=etree.SubElement(spg,'stoppingPoints_List')
        for sp in StoppingPointGroup.allStoppingPointGroups[spgid].spids:
            etree.SubElement(spl,'stoPo_RefId').text=sp

    rproot=etree.SubElement(inf,'runningProfiles')
    rp=etree.SubElement(rproot,'runningProfile')
    rp.set('runProfile_Id','maxspeed')
    etree.SubElement(rp,'name').text="maxspeed"
    etree.SubElement(rp, 'speedRestriction').text = "false"

    jroot=etree.SubElement(inf,'journeys')
    for jname in Journey.allJourneys:
        journey = Journey.allJourneys[jname]
        jel = etree.SubElement(jroot, 'journey')
        jel.set('journey_Id', jname)
        etree.SubElement(jel, 'name').text = jname
        bs = etree.SubElement(jel, 'blockSequence')
        
        index = 0
        for blockref in journey.blockSequence:
            bse = etree.SubElement(bs, 'blockSeqElmt')
            bse.set('index', str(index))
            etree.SubElement(bse, 'blockSection_RefId').text = blockref
            index += 1

        jiroot = etree.SubElement(jel, 'journeyInstances')

        
        for ji_index, journey_instance in enumerate(journey.journeyInstances):  
            ji = etree.SubElement(jiroot, 'journeyInstance')
            ji.set('jouInst_Id', f"{jname}_JourneyInstance_{ji_index}")  
            etree.SubElement(ji, 'rolSto_RefId').text = "DEFAULTRS"  # todo: find rolling stock
            
            sseq = etree.SubElement(ji, 'stoppingSequence')
            sseqidx = 0
            detroot = etree.SubElement(ji, 'journeyInstanceTDSDetails')
            detroot.set('runningProfile_RefId', "maxspeed")
            
            idx = 0
            for jitdet in journey_instance.JITDSDetail: 
                jid = etree.SubElement(detroot, 'journeyInstanceTDSDetail')
                jid.set('index', str(idx))
                idx += 1
                
                etree.SubElement(jid, 'TDS_RefId').text = jitdet.tds
                etree.SubElement(jid, 'runningTime').text = str(jitdet.run)
                etree.SubElement(jid, 'clearingTime').text = str(jitdet.clear)
                
                occupied_tds = etree.SubElement(jid, 'occupiedTDS')
                for occ_tds_ref_id in jitdet.occupied_tds:
                    etree.SubElement(occupied_tds, 'occTDS_RefId').text = occ_tds_ref_id
                    
                if jitdet.stopid != "":
                    etree.SubElement(jid, 'stoPo_RefId').text = str(jitdet.stopid)
                    sseqe = etree.SubElement(sseq, 'stopSeqElmt')
                    sseqe.set('index', str(sseqidx))
                    sseqidx += 1
                    
                    sat = etree.SubElement(sseqe, 'stoppingAt')
                    etree.SubElement(sat, 'stoPo_refId').text = str(jitdet.stopid)
                    
                    stype = "Intermediate"
                    if journey_instance.JITDSDetail[0] == jitdet:
                        stype = "Origin"
                    if journey_instance.JITDSDetail[-1] == jitdet:
                        stype = "Destination"
                    
                    etree.SubElement(sseqe, 'stoppingType').text = stype

    tree = etree.ElementTree(root)
    tree.write(path, pretty_print=True, xml_declaration=True,   encoding="utf-8")
    return path



def loadPath(pname, proot ,infra_file):
    journey=Journey(pname)
    print("Journey Name is ", pname, proot)
    infra_tree = etree.parse(infra_file)
    guids = proot.findall(".//ElementaryRoutes/guid") 
    tcos = proot.findall(".//TrackCircuitOccupation") 

    stop_signaltypes = infra_tree.findall(".//SignalTypes/SignalType/Name")
    stop_paths_list = []
    for a in stop_signaltypes:
        stop_paths_list.append(a.text)
      
    first_guid_track_circuit_name = None
    if guids:
        first_guid = guids[0]
        # print("First guide for the route", pname," is ", first_guid.text)
        elementary_routes = infra_tree.findall(".//ElementaryRoute")
        for route in elementary_routes:
            guid_export = route.find("Guid")
            if guid_export is not None and guid_export.text == first_guid.text:
                signal_names = route.findall(".//Signal")
                if signal_names:
                    first_signal_name = signal_names[0].find("Name").text
                    sig_number_first = signal_names[0].find("NumberOfLevels").text
                    signame_first_signal = f"{first_signal_name}_{sig_number_first}" 
                    # print("First Signal Name:",first_signal_name)
                nameoftrackcircuits = route.findall(".//Signal/TrackCircuits/trackDetectionSection/Name")
                if nameoftrackcircuits:
                    first_guid_track_circuit_name = nameoftrackcircuits[0].text
                    # print("Fist track circuit of signal ", first_signal_name, " is ", first_guid_track_circuit_name)
                    break

    
    first_tcos_track_circuit_name = None
    if tcos:
        first_tcos_track_circuit = tcos[0].find("Name")
        print("sssssssss     ",first_tcos_track_circuit.text)
        if first_tcos_track_circuit is not None:
            first_tcos_track_circuit_name = first_tcos_track_circuit.text
            # print(first_tcos_track_circuit_name)

    
    if first_guid_track_circuit_name and first_tcos_track_circuit_name:
        if first_guid_track_circuit_name == first_tcos_track_circuit_name:
            print(" matches ")
        else:
            print("does not match")
    else:
        print("Could not find")
        exit(2)
   
    before_matching_tcos = []
    match_found = False
    for tco in tcos:
        tco_name_element = tco.find("Name")
        if tco_name_element is not None:
            tco_name = tco_name_element.text
            if tco_name == first_guid_track_circuit_name:
                match_found = True
                break
            before_matching_tcos.append(tco)

    if match_found:
        print("Elements in tcos before the matching element:")
        for elem in before_matching_tcos:
            tco_name_element = elem.find("Name")
            if tco_name_element is not None:
                print("Tds Name:  ",tco_name_element.text)
            # tco_stop_initial = elem.find("StoppingPointGuid")
            # if tco_stop_initial is not None:
            #     Journey.getStopsId
    else:
        print("No matching .")
        exit(1)
    
    tcos_names = []
    for elem in before_matching_tcos:
        tco_name_element = elem.find("Name")
        if tco_name_element is not None:
            tcos_names.append(tco_name_element.text)

    if before_matching_tcos is not None:
        unique_signame = f"VSignal_{'_'.join(tcos_names)}"
        sigid = unique_signame  
        nblev = 3 
        ITSignal.getOrCreate(unique_signame, sigid, nblev) 
        blockname = f"VBlock_{unique_signame}_{signame_first_signal}_{'_'.join(tcos_names)}"
        blockid = blockname
        first_block = Block.getOrCreate(unique_signame,signame_first_signal,tcos_names,blockid,blockname)
        journey.addBlockRef(first_block.name)

    for guid in guids:        
        elementary_routes = infra_tree.findall(".//ElementaryRoute")
        found_match = False    
        track_circuit_names = []      
        for route in elementary_routes:
            guid_export = route.find("Guid")            
            if guid_export is not None and guid_export.text == guid.text:
                print("Name of the guid:", route.find("Name").text) 
                nameoftrackcircuits = route.findall(".//Signal/trackDetectionSection/Name")
                for a in nameoftrackcircuits:
                    first_guid_track_circuit_name = nameoftrackcircuits[0].text
                    print("Track Circuit in this guid: ", a.text)
                    found_match = True
                    track_circuit_names.append(a.text)
                break
        if not found_match:
            print("No matching route found for GUID:", guid.text)
            
            
        if track_circuit_names:
            blocks_with_guid_name = Block.getBlocksByName(guid.text)
            for block in blocks_with_guid_name:
                journey.addBlockRef(block.name)  
    
   

    journey_instance = JourneyInstance(journey)

    
    for index, tco in enumerate(tcos):
        occupied_list_of_tds = []
        name_tco = tco.find("Name").text
        HeadEntryTime = tco.find("HeadEntryTime").text
        TailEntryTime = tco.find("TailEntryTime").text
        HeadExitTime = tco.find("HeadExitTime").text
        TailExitTime = tco.find("TailExitTime").text
        StoppingTime = tco.find("StoppingTime")
        StoppingPointGuid = tco.find("StoppingPointGuid")

        if (name_tco is None or HeadEntryTime is None or 
            TailEntryTime is None or HeadExitTime is None or 
            TailExitTime is None):
            print(f"Missing element in TrackCircuitOccupation: {name_tco}")
            continue

        if StoppingTime is not None:
            stopping_time_sec = get_sec(StoppingTime.text)
        else:
            stopping_time_sec = 0
        
        running_time = get_sec(HeadExitTime) - get_sec(HeadEntryTime) -stopping_time_sec
        clearing_time = get_sec(TailExitTime) - get_sec(HeadExitTime)
        
        if get_sec(HeadExitTime) < get_sec(TailEntryTime):
            print(f"Warning: Head Exit Time ({HeadExitTime}) is lesser than Tail Entry Time ({TailEntryTime}) for {name_tco}" )
            occupied_list_of_tds.append(tcos[index - 1].find("Name").text)
            previous_tds = find_previous_tds_with_condition(tco, tcos, index)
            if previous_tds:
                print("Previous TCOs where the condition is true:")
                for prev_tco in reversed(previous_tds):
                    print(f" Name: {prev_tco.find('Name').text}, Tail Entry Time: {prev_tco.find('TailEntryTime').text}")
                    occupied_list_of_tds.append(prev_tco.find("Name").text)

        stopid = StoppingPointGuid.text if StoppingPointGuid is not None else ""
        # print("Stop ID: ", stopid)
        # print(name_tco,running_time,clearing_time,stopid)
        # print()
        r = int(running_time)
        c = int(clearing_time)
        
        try:
            # print(f"Creating JITDSDetail with: name_tco={name_tco}, run={int(running_time)}, clear={clearing_time}, stopid={stopid}")
            jitds_detail = JITDSDetail(tds=name_tco, run=r, clear=c, stopid=stopid, occupied_tds=occupied_list_of_tds)
            journey_instance.addJITDSDetail(jitds_detail)
        except Exception as e:
            print(f"Error creating JITDSDetail or adding to journey: {e}")
            print(f"Values: name_tco={name_tco}, run={int(running_time)}, clear={clearing_time}, stopid={stopid}")


def find_previous_tds_with_condition(tco, tcos, index):
    if index <= 1:
        return []
    current_tco = tco
    previous_tco = tcos[index - 1]
    
    HeadExitTime = current_tco.find("HeadExitTime").text
    TailEntryTime = previous_tco.find("TailEntryTime").text

    if get_sec(HeadExitTime) < get_sec(TailEntryTime):
        previous_tds = find_previous_tds_with_condition(tco,tcos, index - 1)
        previous_tds.append(tcos[index - 2])
        return previous_tds
    else:
        return []

def find_guid_name(guid, infra_file):
    try:
        tree = etree.parse(infra_file)
        root = tree.getroot()
        for elementary_route in root.findall('.//ElementaryRoute'):
            if elementary_route.findtext('Guid') == guid:
                return elementary_route.findtext('Name')
    except etree.XMLSyntaxError as e:
        print("Error parsing XML:", e)
    return None



def process_path(path_element, train_number, infra_file):
    elementary_routes = path_element.find('.//ElementaryRoutes')
    if elementary_routes is not None:
        guids = elementary_routes.findall('guid')
        if guids:
            # Extract names for all GUIDs
            names = [find_guid_name(guid.text, infra_file) for guid in guids]
            # Create journey name by joining names with an underscore and appending train number
            journey_name = f"{'_'.join(names)}_{train_number}".replace(" ", "_")

            # print(f"Full Name: {journey_name}")
            loadPath(journey_name, path_element, infra_file)

def loadIRTT(file, infra_file):
    try:
        tree = etree.parse(file)
        root = tree.getroot()
        trains_element = root.find('Trains')
        
        if trains_element is not None:
            trains = trains_element.findall('.//Train')
            for train in trains:
                train_number = train.findtext('TrainNumber')
                reference_paths = train.findall('.//ReferencePath')
                for reference_path in reference_paths:
                    process_path(reference_path, train_number,infra_file)

                alternative_paths = train.findall('.//AlternativePaths/TrainVariant')
                for train_variant in alternative_paths:
                    process_path(train_variant, train_number,infra_file)

    except etree.XMLSyntaxError as e:
        print("Error parsing XML:", e)
        exit(1)





def loadIrinf(file,timetable_file):
    tree = etree.parse(file)
    for post in tree.xpath("/RailLabInfrastructureExport/SwitchingPosts/SwitchingPost"):
         postname=post.find("Name").text
         # print("*** "+postname+" ***")
         for elroute in post.xpath("ElementaryRoutes/ElementaryRoute"):
            routename=elroute.find("Name").text
            routeid=elroute.find("Guid").text
            # print("** "+routename+" **")
            blockidx=0
            prevsig=""
            prevtdslist=[]
            for sig in elroute.xpath("Signals/Signal"):
                signame=sig.find("Name").text
                sigid=sig.find("Guid").text
                nblev=sig.find("NumberOfLevels").text
                unique_signame = f"{signame}_{nblev}"
                ITSignal.getOrCreate(unique_signame,sigid,nblev)
                # print("*signame "+unique_signame+" "+nblev+" *")
               
                if(prevsig!=""):
                    if prevtdslist:  # Check if prevtdslist is not empty
                        blockid=routeid+"_"+str(blockidx)
                        blockname=blockid
                        # print(prevsig,unique_signame,prevtdslist,blockid,blockname)
                        Block.getOrCreate(prevsig,unique_signame,prevtdslist,blockid,blockname)
                        # print("*Blockname "+prevsig+" "+unique_signame+"      "+" *")
                        # for x in prevtdslist:
                        #     print("Tracklist " + x + " ", end = " ")
                        # print()


                prevtdslist.clear()
                for tc in sig.xpath("TrackCircuits/trackDetectionSection"):
                    tcname=tc.find("Name").text
                    ittc = ITTrackCircuit.getOrCreate(tcname)
                    for topo_parts in tc.xpath("topologyParts/topologyPart"):
                       
                        topo_id = topo_parts.find("Guid").text
                        # print(f"Processing TopologyPart: {topo_id} for TrackCircuit: {tcname}")
                        topo_name = topo_parts.find("Name").text
                        length = float(topo_parts.find("Lenght").text)
                        speed_normal = int(topo_parts.find("SpeedNormal").text)
                        speed_inverse = int(topo_parts.find("SpeedInverse").text)
                        gradient = int(topo_parts.find("Gradient").text)
                        curve = int(topo_parts.find("Curve").text)
                        
                        
                        vis_start = topo_parts.find("visualization/start")
                        vis_end = topo_parts.find("visualization/end")
                        if vis_start is not None and vis_end is not None:
                            start_x = float(vis_start.get("X"))
                            start_y = float(vis_start.get("Y"))
                            end_x = float(vis_end.get("X"))
                            end_y = float(vis_end.get("Y"))
                            visualization = Visualization(start_x, start_y, end_x, end_y)
                        else:
                            visualization = None
                    
                        
                        topo_part = TopologyPart(topo_id, length, speed_normal, speed_inverse, gradient, curve, visualization)
                        ittc.add_topology_part(topo_part)
                    
                    joint_elements = tc.xpath("topologyParts/topologyPart")
                    if len(joint_elements) > 0:
                        
                        # print(tcname, "is the track circuit")
                        prevtdslist.append(tcname)
                        
                        for joint in joint_elements:
                            jname = joint.find("Name").text
                            jid = joint.find("Guid").text
                            ittc.addJoint(jid)
                            print("\t" + jname)
                            
                       
                        prevsig = unique_signame  
                        # print("Previous Signal: ", prevsig)
                    
                blockidx += 1

    # #This is the new code which find the TDS's from all the TDS attached to the trainpoints for any stopping point
                #TODO: Here it will only give TDS's to the stopping points which are present in the journey instances. This is not the right way as 
                #stooping points which are not there in the jounney instances has not TDS's present in them . Could be correct way though. 


    timetable_tree =  etree.parse(timetable_file)
    train_points = timetable_tree.xpath(".//ReferencePath/TrackCircuitOccupations/TrackCircuitOccupation | .//AlternativePaths/TrainVariant/TrackCircuitOccupations/TrackCircuitOccupation")
    stations = tree.xpath("/RailLabInfrastructureExport/TrainStations/TrainStation")
   
    train_points_map = {}

   
    for tp in train_points:
        stopping_point_guid_elem = tp.find("StoppingPointGuid")
        if stopping_point_guid_elem is not None:
            stopping_point_guid = stopping_point_guid_elem.text
            name_elem = tp.find("Name")
            print("names aresss: ", name_elem)
            name = name_elem.text if name_elem is not None else None
            train_points_map[stopping_point_guid] = name
    for stopping_point_guid, name in train_points_map.items():
        print(f"We have the StoppingPointGuid: {stopping_point_guid}, Name: {name}")
    

                
    for station in stations:
        stid = station.find("Guid").text
        stname = station.find("Name").text
        group=StoppingPointGroup(stid,stname)
        for sp in station.xpath("Tracks/TrainStationTrack/StoppingPoints/StoppingPoint"):
             spname=sp.find("Name").text
             spid=sp.find("Guid").text
             exit_signal = sp.find("ExitSignal").text
             signal_names = tree.xpath("/RailLabInfrastructureExport/SwitchingPosts/SwitchingPost/ElementaryRoutes/ElementaryRoute/Signals/Signal")            
             track_circuits = []
             for signal in signal_names:
                sig_guid = signal.find("Guid").text
                if sig_guid == exit_signal:
                    sig_name = signal.find("Name").text
                    sig_number = signal.find("NumberOfLevels").text
                    signame = f"{sig_name}_{sig_number}" 
                    print(f"Found matching signal for StoppingPoint {spname}: {sig_guid} for {signame}")
                
             for stopping_point_guid, name in train_points_map.items():
                if spid == stopping_point_guid:
                    print("hhhhhhhhhhhhhhhh")
                    track_circuits.append(name)
             for x in track_circuits: 
                print("here are the track cirucuits")


             point=ITStoppingPoint(spname,spid)
             point.addSig(signame)
             for tds in track_circuits:
                 point.addTds(tds)
             group.addStoppingPoint(spid)










#Create Timetable File



journey_name_counts = {}
def process_path_name(path_element, train_number,infra_file):
    elementary_routes = path_element.find('.//ElementaryRoutes')
    if elementary_routes is not None:
        guids = elementary_routes.findall('guid')
        if guids:
            names = [find_guid_name(guid.text, infra_file) for guid in guids]
            journey_name = f"{'_'.join(names)}_{train_number}".replace(" ", "_")

         
            if journey_name not in journey_name_counts:
                journey_name_counts[journey_name] = 0
            
          
            index = journey_name_counts[journey_name]
            
          
            journey_instance_name = f"{journey_name}_JourneyInstance_{index}"

            journey_name_counts[journey_name] += 1

            return journey_instance_name

    return None  
        
        

def calculate_times(xml_file, timetable_export,infra_file):
    tree = etree.parse(xml_file)
    root = tree.getroot()

    xtree = etree.parse(timetable_export)
    xroot = xtree.getroot()

    running_times = {}
    start_times = {}
    end_times = {}
    alternative_journeys = {}
    stop_times = {}
    name_counts = {}

    for trainid in xroot.findall(".//Train"):
        trainnumber = trainid.find('TrainNumber').text
        reference_path = trainid.find('.//ReferencePath')            
        ref_name = process_path_name(reference_path, trainnumber,infra_file)
        print("Train Number: ", trainnumber)

        print("Reference path: ", ref_name)

        alternative_paths = trainid.findall('.//AlternativePaths/TrainVariant')
        alternative_path_names = [process_path_name(ap, trainnumber,infra_file) for ap in alternative_paths]
        alternative_journeys[trainnumber] = alternative_path_names
        

        found_train = False
        for journey_instance in root.findall(".//journeyInstance"):
            ji = journey_instance.get('jouInst_Id')
            if ji == ref_name:
                print(f"Found journey instance matching reference path: {ji}" + " for train ",trainnumber )
                total_running_time = 0
                total_stopping_time = 0
                stops = []
                for detail in journey_instance.findall(".//journeyInstanceTDSDetail"):
                    running_time = int(detail.find('runningTime').text)
                    total_running_time += running_time
                found_train = True
                print("Found train:", trainnumber)
                track_circuit_occupations = trainid.findall(".//ReferencePath/TrackCircuitOccupations/TrackCircuitOccupation")
                if track_circuit_occupations:
                    first_track_circuit_occupation = track_circuit_occupations[0]
                    start_time = first_track_circuit_occupation.find('HeadEntryTime').text.strip().lstrip('0 ')
                    start_time_seconds = hhmmss_to_seconds(start_time)
                    start_times[ ji, trainnumber] = start_time
                    last_track_circuit_occupation = track_circuit_occupations[-1]
                    end_time = last_track_circuit_occupation.find('HeadExitTime').text.strip().lstrip('0 ')
                    end_times[ ji, trainnumber] = end_time

                    # for tco in track_circuit_occupations:
                    #     StoppingTime = tco.find('StoppingTime')
                    #     if StoppingTime is not None:
                    #          stop_time = StoppingTime.text.strip().split('.')[0]
                    #          print(stop_time)
                    #          total_stopping_time += hhmmss_to_seconds(stop_time)
                    # print(f"For journey instance {ji} the information are {start_time_seconds} and {total_running_time} and {total_stopping_time} ")
                    # end_times[ji, trainnumber] = total_running_time + total_stopping_time + start_time_seconds

                train_points = trainid.findall("./ReferencePath//TrainPoint") #Neeraj:  about the First and the Last Track Circuit Stops. It is there is train points but not in Track Circuit
                for tp in train_points:
                    ArrivalTime = tp.find('ArrivalTime')
                    DepartureTime = tp.find('DepartureTime')
                    MinimumStopTime = tp.find('MinimumStopTime')
                    
                    if ArrivalTime is not None and DepartureTime is not None:
                        arrival_time_str = ArrivalTime.text.strip().lstrip('0 ')
                        departure_time_str = DepartureTime.text.strip().lstrip('0 ')
                        arrival_time_sec = hhmmss_to_seconds(arrival_time_str)
                        departure_time_sec = hhmmss_to_seconds(departure_time_str)
                        if MinimumStopTime is not None:
                            minimum_stop_time_str = MinimumStopTime.text.strip()
                            stop_duration = hhmmss_to_seconds(minimum_stop_time_str)
                        else:
                            stop_duration = departure_time_sec - arrival_time_sec
                        print(f"The stop duration for train {trainnumber} at train point {tp.find('Name').text} is {stop_duration}")
                        if stop_duration > 0: 
                            stops.append((arrival_time_sec,departure_time_sec,stop_duration))
                print("finish")
                stop_times[(ji, trainnumber)] = stops

                for key, value in end_times.items():
                    ji, trainnumber = key
                    print(f"End time for train {trainnumber} in segment {ji}: {value} seconds")


        if not found_train:
            print("Train not found for journey instance:", ji)
        


    return start_times, running_times, end_times, stop_times, alternative_journeys



def create_output_xml(start_times, running_times, end_times, stop_times, alternative_journeys, connections_data):
    root = etree.Element('recifeObjects')
    timetable_definition = etree.SubElement(root, 'timetableDefinition', timetable_id="Mandelieu_Vint_Reduced")

    etree.SubElement(timetable_definition, 'name').text = "Mandelieu_Vint_Reduced"
    etree.SubElement(timetable_definition, 'description').text = "Generated with IngeTime2Recife python script (GML)"
    etree.SubElement(timetable_definition, 'startDate').text = "1980-01-01"
    etree.SubElement(timetable_definition, 'endDate').text = "1980-01-01"

    course_types = etree.SubElement(timetable_definition, 'courseTypes')
    course_type = etree.SubElement(course_types, 'courseType', courseType_Id="CT")
    etree.SubElement(course_type, 'name').text = "CT"
    etree.SubElement(course_type, 'inObjFunc').text = "true"
    etree.SubElement(course_type, 'priorityFactor').text = "1"

    courses = etree.SubElement(timetable_definition, 'courses')

    for (ji, trainnumber), start_time in start_times.items():
        course_id = trainnumber

        course = etree.SubElement(courses, 'course', course_Id=course_id)
        etree.SubElement(course, 'name').text = course_id
        etree.SubElement(course, 'courseType_RefId').text = "CT"
        etree.SubElement(course, 'description').text = ""
        etree.SubElement(course, 'defJourneyInstance_RefId').text = ji

        if trainnumber in alternative_journeys:
            alt_journeys = alternative_journeys[trainnumber]
            alternative_journeys_element = etree.SubElement(course, 'alternativeJourneys')
            for alt_journey in alt_journeys:
                alt_journey_element = etree.SubElement(alternative_journeys_element, 'altJourneyInstance_RefId')
                alt_journey_element.text = alt_journey

        repeat_every = etree.SubElement(course, 'repeatEvery')
        etree.SubElement(repeat_every, 'weekday').text = "Everyday"

        entrance_time = etree.SubElement(course, 'entranceTime')
        etree.SubElement(entrance_time, 'day').text = "0"
        etree.SubElement(entrance_time, 'time').text = start_time

        if (ji, trainnumber) in end_times:
            end_time = end_times[(ji, trainnumber)]
            exit_time = etree.SubElement(course, 'exitTime')
            etree.SubElement(exit_time, 'day').text = "0"
            etree.SubElement(exit_time, 'time').text = end_time


        if (ji, trainnumber) in stop_times:
            idx = 0
            stops_specifications = etree.SubElement(course, 'stopsSpecifications')
            for idx, (arrival_time_sec,departure_time_sec,stop_duration) in enumerate(stop_times[(ji, trainnumber)]):
                stop_specification = etree.SubElement(stops_specifications, 'stopSpecification', StoSeqElmt_RefIdx=str(idx))
                scheduled_arrival = etree.SubElement(stop_specification, 'scheduledArrivalTime')
                etree.SubElement(scheduled_arrival, 'day').text = "0"
                etree.SubElement(scheduled_arrival, 'time').text = seconds_to_hhmmss(arrival_time_sec)
                scheduled_departure = etree.SubElement(stop_specification, 'scheduledDepartureTime')
                etree.SubElement(scheduled_departure, 'day').text = "0"
                etree.SubElement(scheduled_departure, 'time').text = seconds_to_hhmmss(departure_time_sec)
                etree.SubElement(stop_specification, 'minimumDwellTime').text = str(stop_duration)
                etree.SubElement(stop_specification, 'optionalStop').text = "0"
                idx= idx+1

        # Add the connections branch
    connections = etree.SubElement(timetable_definition, 'connections')
    for connection_id, connection_info in connections_data.items():
        connection = etree.SubElement(connections, 'connection', connection_Id=connection_id)
        etree.SubElement(connection, 'arrivingCourse_RefId').text = connection_info['arrivingCourse_RefId']
        etree.SubElement(connection, 'departingCourse_RefId').text = connection_info['departingCourse_RefId']
        etree.SubElement(connection, 'minimumDuration').text = str(connection_info['minimumDuration'])
        etree.SubElement(connection, 'maximumTolerance').text = str(connection_info['maximumTolerance'])
        etree.SubElement(connection, 'atStoGro_refId').text = connection_info['atStoGro_refId']
        etree.SubElement(connection, 'connectionType').text = connection_info['connectionType']

    return root


def create_connection_data(timetable_path):
    tree = etree.parse(timetable_path)
    root = tree.getroot()
    train_data = {}
    for train in root.findall(".//Train"):
        trainnumber = train.find('TrainNumber').text
        train_guid = train.find('TrainGuid').text
        train_data[train_guid] = {
            'TrainNumber': trainnumber,
            'TrainGuid': train_guid,
            'VehiceReuseTrains': train.find('VehiceReuseTrains/guid').text if train.find('VehiceReuseTrains/guid') is not None else None
        }
    connections_data = {}
    connection_count = 1  
    for train in root.findall(".//Train"):
        trainnumber = train.find('TrainNumber').text
        train_guid = train.find('TrainGuid').text
        reuse_guid = train.find('VehiceReuseTrains/guid').text if train.find('VehiceReuseTrains/guid') is not None else None
        if reuse_guid:
            arriving_train = trainnumber 
            atStoGro_refId = None
            for train_point in reversed(train.findall(".//ReferencePath/TrainPoints/TrainPoint")):
                if train_point.find("Type").text == "Train station":
                    atStoGro_refId = train_point.find('Name').text
                    break     
            departing_train = next((t['TrainNumber'] for t in train_data.values() if t['TrainGuid'] == reuse_guid), None)
            if departing_train:             
                connection = {
                    'arrivingCourse_RefId': arriving_train,
                    'departingCourse_RefId': departing_train,
                    'minimumDuration': 300,  
                    'maximumTolerance': 86400,  
                    'atStoGro_refId': atStoGro_refId, 
                    'connectionType': "RollingStock-Balance"    
                }
                connections_data[f"C{connection_count}"] = connection
                connection_count += 1  
    return connections_data






#Create Perturbation File
    

    
def generate_perturbations(course_ids):
    recifeObjects = etree.Element('recifeObjects')
    PerturbationScenarioDefinition = etree.SubElement(recifeObjects, 'PerturbationScenarioDefinition')
    perturbationsList = etree.SubElement(PerturbationScenarioDefinition, 'perturbationsList')

    for course_id in course_ids:
        perturbation = etree.SubElement(perturbationsList, 'perturbation', {'perturbation_Id': f'perturbation_{course_id}'})
        entranceDelayPert = etree.SubElement(perturbation, 'entranceDelayPert')
        course_RefId = etree.SubElement(entranceDelayPert, 'course_RefId')
        course_RefId.text = str(course_id)
        value = etree.SubElement(entranceDelayPert, 'value')
        value.text = str(random.randint(1000, 5000))

    return recifeObjects

def extract_course_ids(xml_file):
    tree = etree.parse(xml_file)
    root = tree.getroot()
    trainnumbers = [trainid.find('TrainNumber').text for trainid in root.findall(".//Train")]
    return trainnumbers




def process_files(timetable_file, infra_file,Vehicles_file,TrainSetTempletes_file, output_dir):
    # Validate input files
    if not os.path.exists(timetable_file):
        raise FileNotFoundError(f"Timetable file not found: {timetable_file}")
    if not os.path.exists(infra_file):
        raise FileNotFoundError(f"Infrastructure file not found: {infra_file}")
    if not os.path.exists(Vehicles_file):
        raise FileNotFoundError(f"Extra file not found: {Vehicles_file}")
    if not os.path.exists(TrainSetTempletes_file):
        raise FileNotFoundError(f"Extra file not found: {TrainSetTempletes_file}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file1 = os.path.join(output_dir, f"infra_{timestamp}.xml")
    output_file2 = os.path.join(output_dir, f"rolling_stock_{timestamp}.xml")
    output_file3 = os.path.join(output_dir, f"timetable_{timestamp}.xml")
    output_file4 = os.path.join(output_dir, f"perturbation_{timestamp}.xml")

    

      # Placeholder processing logic
    print(f"Processing {timetable_file}, {infra_file}, {Vehicles_file}, and {TrainSetTempletes_file}..")

    infname="Mandelieu_Vint_Reduced"
 # Creating_Infra and Rolling_Stock
    loadIrinf(infra_file,timetable_file)
    loadIRTT(timetable_file, infra_file)

    Created_Infra_File = saveInfra(output_file1,infname)
    vehicle_details = read_vehicle_details_from_xml(Vehicles_file)
    rolling_stock_details = read_rolling_stock_details_from_xml(TrainSetTempletes_file)
    saveRS(output_file2,infname,vehicle_details,rolling_stock_details)

 # Creating_Timetable
 
    connections_data = create_connection_data(timetable_file)
    start_times, running_times, end_times, stop_times, alternative_journeys = calculate_times(Created_Infra_File, timetable_file,infra_file)
    output_xml_root = create_output_xml(start_times, running_times, end_times, stop_times, alternative_journeys,connections_data)

    pretty_xml_as_string = prettify(output_xml_root)
    with open(output_file3, 'w', encoding='utf-8') as f:
        f.write(pretty_xml_as_string)


 # Creating_Perturbations
    try:
        course_ids = extract_course_ids(timetable_file)
        print(f"Extracted course IDs: {course_ids}") 
        if not course_ids:
            raise ValueError("No course IDs found in the XML file.")
        
        disturbance_file = generate_perturbations(course_ids)
        perturbation_xml_output = prettify(disturbance_file)

        with open(output_file4, 'w') as file:
            file.write(perturbation_xml_output)
        
        print("Perturbation XML file has been created successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")




if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Process three input files and produce four output files.")
    parser.add_argument("timetable_file", help="Path to the timetable file")
    parser.add_argument("infra_file", help="Path to the infrastructure file")
    parser.add_argument("Vehicles_file", help="Path to the extra input file")
    parser.add_argument("TrainSetTempletes_file", help="Path to the extra input file")
    parser.add_argument("output_dir", help="Directory to store output files")


    args = parser.parse_args()

    process_files(args.timetable_file, args.infra_file,args.Vehicles_file,args.TrainSetTempletes_file, args.output_dir)
