import json
import re

from openhands_aci import file_editor

filepath = '/home/ubuntu/adityabs/openhands-aci/file.go'
op = file_editor(command='view', path=filepath)
matches = re.findall(
    r'<oh_aci_output_[0-9a-f]{32}>(.*?)</oh_aci_output_[0-9a-f]{32}>', op, re.DOTALL
)

if len(matches) == 1:
    # Use specific actions/observations types
    match = matches[0]
    try:
        result_dict = json.loads(match)
        print(result_dict['formatted_output_and_error'])
    except json.JSONDecodeError:
        # Handle JSON decoding errors if necessary
        print(f"Invalid JSON in 'openhands-aci' output: {match}")
else:
    for match in matches:
        try:
            result_dict = json.loads(match)
            print(result_dict['formatted_output_and_error'])
        except json.JSONDecodeError:
            # Handle JSON decoding errors if necessary
            print(f"Invalid JSON in 'openhands-aci' output: {match}")
