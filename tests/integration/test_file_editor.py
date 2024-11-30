import json
import re

import pytest

from openhands_aci.editor import file_editor
from openhands_aci.editor.prompts import NAVIGATION_TIPS


@pytest.fixture
def temp_file(tmp_path):
    # Set up a temporary directory with test files
    test_file = tmp_path / 'test_file.txt'
    test_file.write_text('This is a test file.\nThis file is for testing purposes.')
    return str(test_file)


def test_file_editor_happy_path(temp_file):
    command = 'str_replace'
    old_str = 'test file'
    new_str = 'sample file'

    # Call the `file_editor` function
    result = file_editor(
        command=command,
        path=temp_file,
        old_str=old_str,
        new_str=new_str,
        enable_linting=False,
    )

    # Extract the JSON content using a regular expression
    match = re.search(r'<oh_aci_output>(.*?)</oh_aci_output>', result, re.DOTALL)
    assert match, 'Output does not contain the expected <oh_aci_output> tags.'
    result_dict = json.loads(match.group(1))

    # Validate the formatted output in the result dictionary
    formatted_output = result_dict['formatted_output_and_error']
    assert (
        formatted_output
        == f"""The file {temp_file} has been edited. Here's the result of running `cat -n` on a snippet of {temp_file}:
     1\tThis is a sample file.
     2\tThis file is for testing purposes.
Review the changes and make sure they are as expected. Edit the file again if necessary.
{NAVIGATION_TIPS}"""
    )
    assert result_dict['path'] == temp_file
    assert result_dict['prev_exist'] is True
    assert (
        result_dict['old_content']
        == 'This is a test file.\nThis file is for testing purposes.'
    )
    assert (
        result_dict['new_content']
        == 'This is a sample file.\nThis file is for testing purposes.'
    )

    # Ensure the file content was updated
    with open(temp_file, 'r') as f:
        content = f.read()
    assert 'This is a sample file.' in content
