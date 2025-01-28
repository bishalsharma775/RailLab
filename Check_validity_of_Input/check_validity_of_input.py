"""
This script processes railway timetable files (.irtt) against a given infrastructure file (.irinf)
to identify inconsistencies between track circuits.

Usage:
    python script.py -t <timetable_files_dir> -i <infra_file_path> -o <output_dir>

Arguments:
    -t, --timetable_dir: Directory containing timetable files (.irtt).
    -i, --infra_file: Path to the infrastructure file (.irinf).
    -o, --output_dir: Directory where output files will be saved.

Dependencies:
    - lxml for XML parsing
"""

import os
from lxml import etree
import argparse
from datetime import datetime

def find_guids(guid, infra_file):
    # Existing find_guids function
    try:
        tree = etree.parse(infra_file)
        root = tree.getroot()
        for elementary_route in root.findall('.//ElementaryRoute'):
            if elementary_route.findtext('Guid') == guid:
                route_name = elementary_route.findtext('Name')
                track_circuit_names = []
                track_circuits = elementary_route.findall('.//TDS_Topology_List/TDS_Topology')
                for track_circuit in track_circuits:
                    circuit_name = track_circuit.findtext('TDS_RefId')
                    if circuit_name:
                        for trackc in root.findall('.//TrackCircuits/trackDetectionSection'):
                            if trackc.findtext('Guid') == circuit_name:
                                track_circuit_names.append(trackc.findtext('Name'))
                return {
                    'route_name': route_name,
                    'track_circuit_names': track_circuit_names
                }
    except etree.XMLSyntaxError as e:
        print("Error parsing XML:", e)
    return None


def process_path(path_element, train_number, path_type, path_index, output_file, infra_file):
    # Existing process_path function
    guid_infos = []
    elementary_routes = path_element.find('.//ElementaryRoutes')
    if elementary_routes is not None:
        guids = elementary_routes.findall('guid')
        for g in guids:
            guid = g.text
            guid_info = find_guids(guid, infra_file)
            if guid_info:
                guid_infos.append(guid_info)
            if not guid_info:
                exit(1)
    
    track_circuit_occupations = path_element.findall('.//TrackCircuitOccupations/TrackCircuitOccupation')
    names_list = []
    for occupation in track_circuit_occupations:
        name = occupation.findtext('Name')
        HeadEntryTime = occupation.find("HeadEntryTime").text
        TailEntryTime = occupation.find("TailEntryTime").text
        HeadExitTime = occupation.find("HeadExitTime").text
        TailExitTime = occupation.find("TailExitTime").text

        if HeadEntryTime is None or TailEntryTime is None or HeadExitTime is None or TailExitTime is None:
            output_file.write(f"For Train: {train_number}  {path_type}  {path_index}\n")
            output_file.write(f"Warning: TrackCircuitOccupation '{name}' is missing one or more time values for HeadEntryTime, TailEntryTime, HeadExitTime, or TailExitTime.\n")
        if name:
            names_list.append(name)
    
    if names_list:
        names_list = names_list[1:]
    
    for track_circuit_name in guid_info['track_circuit_names']:
        if track_circuit_name not in names_list:
            output_file.write(f"For Train: {train_number}  {path_type}  {path_index}\n")
            output_file.write(f"Inconsistency found in route '{guid_info['route_name']}': Track Circuit '{track_circuit_name}' not in timetable file but in infra file.\n")

    for name in names_list:
        found_in_guid_info = False
        for info in guid_infos:
            if name in info['track_circuit_names']:
                found_in_guid_info = True
                break
        if not found_in_guid_info:
            output_file.write(f"For Train: {train_number}  {path_type}  {path_index}\n")
            output_file.write(f"Extra Track Circuit found in timetable file: Track Circuit '{name}'\n")

    names_list_count = len(names_list)
    guid_infos_total_track_circuits = sum(len(info['track_circuit_names']) for info in guid_infos)
    if names_list_count != guid_infos_total_track_circuits:
        output_file.write(f"For Train: {train_number}  {path_type}  {path_index}\n")
        output_file.write(f"Number of track circuits {names_list_count} in timetable file does not match number of TC for all elementary routes in infra file {guid_infos_total_track_circuits}.\n")
    
    output_file.write("__________________________________________________________________________________________________________________\n")


def loadIRTT(timetable_file, output_file_path, infra_file):
    # Existing loadIRTT function
    try:
        with open(output_file_path, 'w') as output_file:
            tree = etree.parse(timetable_file)
            root = tree.getroot()
            trains_element = root.find('Trains')
            
            if trains_element is not None:
                trains = trains_element.findall('.//Train')
                for train in trains:
                    train_number = train.findtext('TrainNumber')
                    output_file.write(f"Train Number: {train_number}\n")
                    
                    reference_paths = train.findall('.//ReferencePath')
                    for idx, reference_path in enumerate(reference_paths):
                        process_path(reference_path, train_number, "Reference Path", idx + 1, output_file, infra_file)
                    output_file.write("\n")
                
                    alternative_paths = train.findall('.//AlternativePaths/TrainVariant')
                    for idx, train_variant in enumerate(alternative_paths):
                        process_path(train_variant, train_number, "Train Variant", idx + 1, output_file, infra_file)
                        output_file.write("\n")
    except etree.XMLSyntaxError as e:
        print(f"Error parsing XML for file {timetable_file}: {e}")
        exit(1)

def process_multiple_timelines(timetable_files_dir, infra_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for timetable_file in os.listdir(timetable_files_dir):
        if timetable_file.endswith('.irtt'):  # Ensure we process only .irtt files
            timetable_file_path = os.path.join(timetable_files_dir, timetable_file)
            output_file_name = os.path.splitext(timetable_file)[0] + "_output.txt"
            output_file_path = os.path.join(output_dir, output_file_name)

            print(f"Processing: {timetable_file_path} -> {output_file_path}")
            loadIRTT(timetable_file_path, output_file_path, infra_file)


# Main function with parser
if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Process timetable files and check consistency with infrastructure files.")
    parser.add_argument("timetable_dir", help="Directory containing timetable files (.irtt)")
    parser.add_argument("infra_file", help="Infrastructure file (.irinf) path")
    parser.add_argument("output_dir", help="Output directory for results")

    # Parse arguments
    args = parser.parse_args()

    # Call the processing function with user-provided paths
    process_multiple_timelines(args.timetable_dir, args.infra_file, args.output_dir)
