# Railway Timetable Processor
This script processes railway timetable files and compares them with an infrastructure file to identify inconsistencies.

## Requirements
- Python 3.x
- lxml library

## Usage
1. Clone or download this repository to your local machine.
2. Ensure your timetable files (`.irtt`) are stored in a single directory.  
   Prepare the infrastructure file (`.irinf`) in a valid XML format.
3. Run the script with the following command:
   ```bash
   python script.py <timetable_dir> <infra_file> <output_dir>

