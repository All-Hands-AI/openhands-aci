"""Tests for file validation in file editor."""

from openhands_aci.editor import file_editor

from .conftest import parse_result


def test_file_validation(temp_file):
    """Test file validation for various file types."""
    # Test binary file
    with open(temp_file, 'wb') as f:
        f.write(b'Some text\x00with binary\x00content')

    result = file_editor(
        command='view',
        path=temp_file,
        enable_linting=False,
    )
    result_json = parse_result(result)
    assert 'binary' in result_json['formatted_output_and_error'].lower()

    # Test large file
    large_size = 11 * 1024 * 1024  # 11MB
    with open(temp_file, 'w') as f:
        f.write('x' * large_size)

    result = file_editor(
        command='view',
        path=temp_file,
        enable_linting=False,
    )
    result_json = parse_result(result)
    assert 'too large' in result_json['formatted_output_and_error']
    assert '10MB' in result_json['formatted_output_and_error']

    # Test SQL file
    sql_content = """
    SELECT *
    FROM users
    WHERE id = 1;
    """
    with open(temp_file, 'w') as f:
        f.write(sql_content)

    result = file_editor(
        command='view',
        path=temp_file,
        enable_linting=False,
    )
    result_json = parse_result(result)
    assert 'SELECT *' in result_json['formatted_output_and_error']
    assert 'binary' not in result_json['formatted_output_and_error'].lower()
