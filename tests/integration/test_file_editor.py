import json
import re

import pytest

from openhands_aci.editor import file_editor


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
    match = re.search(
        r'<oh_aci_output_[0-9a-f]{32}>(.*?)</oh_aci_output_[0-9a-f]{32}>',
        result,
        re.DOTALL,
    )
    assert match, 'Output does not contain the expected <oh_aci_output_> tags in the correct format.'
    result_dict = json.loads(match.group(1))

    # Validate the formatted output in the result dictionary
    formatted_output = result_dict['formatted_output_and_error']
    assert (
        formatted_output
        == f"""The file {temp_file} has been edited. Here's the result of running `cat -n` on a snippet of {temp_file}:
     1\tThis is a sample file.
     2\tThis file is for testing purposes.
Review the changes and make sure they are as expected. Edit the file again if necessary."""
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


def test_file_editor_with_xml_tag_parsing(temp_file):
    # Create content that includes the XML tag pattern
    xml_content = """This is a file with XML tags parsing logic...
match = re.search(
    r'<oh_aci_output_[0-9a-f]{32}>(.*?)</oh_aci_output_[0-9a-f]{32}>',
    result,
    re.DOTALL,
)
...More text here.
"""

    with open(temp_file, 'w') as f:
        f.write(xml_content)

    result = file_editor(
        command='view',
        path=temp_file,
    )

    # Ensure the content is extracted correctly
    match = re.search(
        r'<oh_aci_output_[0-9a-f]{32}>(.*?)</oh_aci_output_[0-9a-f]{32}>',
        result,
        re.DOTALL,
    )

    assert match, 'Output does not contain the expected <oh_aci_output_> tags in the correct format.'
    result_dict = json.loads(match.group(1))

    # Validate the formatted output in the result dictionary
    formatted_output = result_dict['formatted_output_and_error']
    print(formatted_output)
    assert (
        formatted_output
        == f"""Here's the result of running `cat -n` on {temp_file}:
     1\tThis is a file with XML tags parsing logic...
     2\tmatch = re.search(
     3\t    r'<oh_aci_output_[0-9a-f]{{32}}>(.*?)</oh_aci_output_[0-9a-f]{{32}}>',
     4\t    result,
     5\t    re.DOTALL,
     6\t)
     7\t...More text here.
     8\t
"""
    )
