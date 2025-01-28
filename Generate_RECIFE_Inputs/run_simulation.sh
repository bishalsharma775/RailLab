#!/bin/bash

# Input directory where timetable files are located
TIMETABLES_DIR="$(pwd)/inputs/timetables"  
INFRA_FILE="$(pwd)/inputs/infra_file.irinf"
VEHICLES_FILE="$(pwd)/inputs/Vehicles.xml"
TRAIN_SET_TEMPLATES_FILE="$(pwd)/inputs/TrainSetTempletes.xml"


OUTPUT_DIR="$(pwd)/outputs"


echo "Timetables directory: $TIMETABLES_DIR"
echo "Infra file: $INFRA_FILE"
echo "Vehicles file: $VEHICLES_FILE"
echo "Train set templates file: $TRAIN_SET_TEMPLATES_FILE"
echo "Output directory: $OUTPUT_DIR"


mkdir -p "$OUTPUT_DIR"


if [ ! -d "$OUTPUT_DIR" ]; then
  echo "Error: Output directory does not exist or cannot be created!"
  exit 1
fi


for TIMETABLE_FILE in "$TIMETABLES_DIR"/*.irtt; do
  
  TIMETABLE_NAME=$(basename "$TIMETABLE_FILE" .irtt)

 
  TIMETABLE_OUTPUT_DIR="$OUTPUT_DIR/$TIMETABLE_NAME"
  mkdir -p "$TIMETABLE_OUTPUT_DIR"


  if [ ! -d "$TIMETABLE_OUTPUT_DIR" ]; then
    echo "Error: Output directory for $TIMETABLE_NAME does not exist or cannot be created!"
    exit 1
  fi

  # Run the Python script for this specific timetable file
  python3 src/generate_files.py "$TIMETABLE_FILE" "$INFRA_FILE" "$VEHICLES_FILE" "$TRAIN_SET_TEMPLATES_FILE" "$TIMETABLE_OUTPUT_DIR"
done
