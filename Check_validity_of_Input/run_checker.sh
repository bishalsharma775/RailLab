#!/bin/bash

# Set paths
TIMETABLE_DIR="$(pwd)/timetable_files"
INFRA_FILE="$(pwd)/infra_file.irinf"
OUTPUT_DIR="$(pwd)/output"


# Run the main Python script
python3 check_validity_of_input.py "$TIMETABLE_DIR" "$INFRA_FILE" "$OUTPUT_DIR"

