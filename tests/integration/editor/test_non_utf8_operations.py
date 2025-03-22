"""Integration tests for editor operations with non-UTF-8 encoded files."""

import os
import tempfile
from pathlib import Path

import pytest

from openhands_aci.editor import file_editor
from openhands_aci.editor.encoding import EncodingManager

from .conftest import parse_result


@pytest.fixture
def temp_non_utf8_file():
    """Create a temporary file with cp1251 encoding for testing."""
    fd, path = tempfile.mkstemp()
    os.close(fd)

    # Create a file with cp1251 encoding containing Russian text
    with open(path, 'wb') as f:
        f.write('# -*- coding: cp1251 -*-\n\n'.encode('cp1251'))
        f.write('# Тестовый файл с кириллицей\n'.encode('cp1251'))
        f.write('text = "Привет, мир!"\n'.encode('cp1251'))
        f.write('numbers = [1, 2, 3, 4, 5]\n'.encode('cp1251'))
        f.write('message = "Это тестовая строка"\n'.encode('cp1251'))

    yield Path(path)
    os.unlink(path)


def test_view_non_utf8_file(temp_non_utf8_file):
    """Test viewing a non-UTF-8 encoded file."""
    # View the file
    result = file_editor(
        command='view',
        path=str(temp_non_utf8_file),
    )

    # Parse the result
    result_json = parse_result(result)

    # Verify the content was read correctly
    assert 'Привет, мир!' in result_json['formatted_output_and_error']
    assert 'Тестовый файл с кириллицей' in result_json['formatted_output_and_error']
    assert 'Это тестовая строка' in result_json['formatted_output_and_error']


def test_view_range_non_utf8_file(temp_non_utf8_file):
    """Test viewing a specific range of a non-UTF-8 encoded file."""
    # View only lines 3-5
    result = file_editor(
        command='view',
        path=str(temp_non_utf8_file),
        view_range=[3, 5],
    )

    # Parse the result
    result_json = parse_result(result)

    # Verify the content was read correctly
    assert 'Тестовый файл с кириллицей' in result_json['formatted_output_and_error']
    assert 'Привет, мир!' in result_json['formatted_output_and_error']

    # Verify that line 6 is not included
    assert 'Это тестовая строка' not in result_json['formatted_output_and_error']


def test_str_replace_non_utf8_file(temp_non_utf8_file):
    """Test replacing text in a non-UTF-8 encoded file."""
    # Replace text
    result = file_editor(
        command='str_replace',
        path=str(temp_non_utf8_file),
        old_str='Привет, мир!',
        new_str='Здравствуй, мир!',
        enable_linting=False,
    )

    # Parse the result
    result_json = parse_result(result)

    # Verify the replacement was successful
    assert 'Здравствуй, мир!' in result_json['formatted_output_and_error']
    assert 'Привет, мир!' not in result_json['formatted_output_and_error']

    # Verify the file was saved with the correct encoding
    with open(temp_non_utf8_file, 'rb') as f:
        content = f.read()

    try:
        decoded = content.decode('cp1251')
        assert 'Здравствуй, мир!' in decoded
    except UnicodeDecodeError:
        pytest.fail('File was not saved with the correct encoding')


def test_insert_non_utf8_file(temp_non_utf8_file):
    """Test inserting text in a non-UTF-8 encoded file."""
    # Insert text after line 4
    result = file_editor(
        command='insert',
        path=str(temp_non_utf8_file),
        insert_line=4,
        new_str='new_var = "Новая переменная"',
        enable_linting=False,
    )

    # Parse the result
    result_json = parse_result(result)

    # Verify the insertion was successful
    assert 'Новая переменная' in result_json['formatted_output_and_error']

    # Verify the file was saved with the correct encoding
    with open(temp_non_utf8_file, 'rb') as f:
        content = f.read()

    try:
        decoded = content.decode('cp1251')
        assert 'Новая переменная' in decoded
    except UnicodeDecodeError:
        pytest.fail('File was not saved with the correct encoding')


def test_create_non_utf8_file():
    """Test creating a new file with non-UTF-8 content."""
    # Create a temporary path
    fd, path = tempfile.mkstemp()
    os.close(fd)
    os.unlink(path)  # Remove the file so we can create it with the editor

    try:
        # Create content with Russian characters
        content = '# -*- coding: cp1251 -*-\n\n'
        content += '# Новый файл с кириллицей\n'
        content += 'greeting = "Привет из нового файла!"\n'

        # Create the file
        result = file_editor(
            command='create',
            path=path,
            file_text=content,
            enable_linting=False,
        )

        # Parse the result
        result_json = parse_result(result)

        # Verify the file was created successfully
        assert 'File created successfully' in result_json['formatted_output_and_error']

        # Read the file with cp1251 encoding to verify content
        encoding_manager = EncodingManager()
        encoding = encoding_manager.detect_encoding(Path(path))

        with open(path, 'r', encoding=encoding) as f:
            file_content = f.read()

        assert 'Привет из нового файла!' in file_content
        assert 'Новый файл с кириллицей' in file_content

    finally:
        # Clean up
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def test_undo_edit_non_utf8_file(temp_non_utf8_file):
    """Test undoing an edit in a non-UTF-8 encoded file."""
    # First, make a change
    file_editor(
        command='str_replace',
        path=str(temp_non_utf8_file),
        old_str='Привет, мир!',
        new_str='Здравствуй, мир!',
        enable_linting=False,
    )

    # Now undo the change
    result = file_editor(
        command='undo_edit',
        path=str(temp_non_utf8_file),
        enable_linting=False,
    )

    # Parse the result
    result_json = parse_result(result)

    # Verify the undo was successful
    assert 'undone successfully' in result_json['formatted_output_and_error']

    # Verify the original content was restored with the correct encoding
    with open(temp_non_utf8_file, 'rb') as f:
        content = f.read()

    try:
        decoded = content.decode('cp1251')
        assert 'Привет, мир!' in decoded
        assert 'Здравствуй, мир!' not in decoded
    except UnicodeDecodeError:
        pytest.fail('File was not restored with the correct encoding')


def test_complex_workflow_non_utf8_file(temp_non_utf8_file):
    """Test a complex workflow with multiple operations on a non-UTF-8 encoded file."""
    # 1. View the file
    result = file_editor(
        command='view',
        path=str(temp_non_utf8_file),
    )
    result_json = parse_result(result)
    assert 'Привет, мир!' in result_json['formatted_output_and_error']

    # 2. Replace text
    result = file_editor(
        command='str_replace',
        path=str(temp_non_utf8_file),
        old_str='Привет, мир!',
        new_str='Здравствуй, мир!',
        enable_linting=False,
    )
    result_json = parse_result(result)
    assert 'Здравствуй, мир!' in result_json['formatted_output_and_error']

    # 3. Insert text
    result = file_editor(
        command='insert',
        path=str(temp_non_utf8_file),
        insert_line=5,
        new_str='# Добавленная строка\nboolean_var = True',
        enable_linting=False,
    )
    result_json = parse_result(result)
    assert 'Добавленная строка' in result_json['formatted_output_and_error']

    # 4. View specific range
    result = file_editor(
        command='view',
        path=str(temp_non_utf8_file),
        view_range=[5, 7],
    )
    result_json = parse_result(result)
    assert 'Добавленная строка' in result_json['formatted_output_and_error']
    assert 'boolean_var = True' in result_json['formatted_output_and_error']

    # 5. Undo the last edit
    result = file_editor(
        command='undo_edit',
        path=str(temp_non_utf8_file),
        enable_linting=False,
    )
    result_json = parse_result(result)
    assert 'undone successfully' in result_json['formatted_output_and_error']

    # 6. Verify the file content after all operations
    with open(temp_non_utf8_file, 'rb') as f:
        content = f.read()

    try:
        decoded = content.decode('cp1251')
        assert 'Здравствуй, мир!' in decoded  # From step 2
        assert 'Добавленная строка' not in decoded  # Undone in step 5
    except UnicodeDecodeError:
        pytest.fail('File was not maintained with the correct encoding')


def test_binary_file_handling():
    """Test handling of binary files that can't be decoded."""
    # Create a temporary binary file
    fd, path = tempfile.mkstemp()
    os.close(fd)

    try:
        # Write some binary data that can't be decoded as text
        with open(path, 'wb') as f:
            f.write(bytes([0x8F, 0x8F, 0x8F, 0x8F]))  # Invalid bytes for most encodings

        # Try to view the file
        result = file_editor(
            command='view',
            path=path,
        )
        result_json = parse_result(result)
        assert 'file appears to be binary' in result_json['formatted_output_and_error'].lower()

    finally:
        # Clean up
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass


def test_mixed_encoding_workflow():
    """Test workflow with files of different encodings."""
    # Create two temporary files with different encodings
    fd1, path1 = tempfile.mkstemp()
    fd2, path2 = tempfile.mkstemp()
    os.close(fd1)
    os.close(fd2)

    try:
        # Create a cp1251 encoded file
        with open(path1, 'wb') as f:
            f.write('# -*- coding: cp1251 -*-\n'.encode('cp1251'))
            f.write('text_cp1251 = "Текст в кодировке CP1251"\n'.encode('cp1251'))

        # Create a UTF-8 encoded file
        with open(path2, 'w', encoding='utf-8') as f:
            f.write('# -*- coding: utf-8 -*-\n')
            f.write('text_utf8 = "Текст в кодировке UTF-8"\n')

        # 1. View the cp1251 file
        result1 = file_editor(
            command='view',
            path=path1,
        )
        result_json1 = parse_result(result1)
        assert 'Текст в кодировке CP1251' in result_json1['formatted_output_and_error']

        # 2. View the UTF-8 file
        result2 = file_editor(
            command='view',
            path=path2,
        )
        result_json2 = parse_result(result2)
        assert 'Текст в кодировке UTF-8' in result_json2['formatted_output_and_error']

        # 3. Edit the cp1251 file
        result3 = file_editor(
            command='str_replace',
            path=path1,
            old_str='Текст в кодировке CP1251',
            new_str='Измененный текст в CP1251',
            enable_linting=False,
        )
        result_json3 = parse_result(result3)
        assert 'Измененный текст в CP1251' in result_json3['formatted_output_and_error']

        # 4. Edit the UTF-8 file
        result4 = file_editor(
            command='str_replace',
            path=path2,
            old_str='Текст в кодировке UTF-8',
            new_str='Измененный текст в UTF-8',
            enable_linting=False,
        )
        result_json4 = parse_result(result4)
        assert 'Измененный текст в UTF-8' in result_json4['formatted_output_and_error']

        # 5. Verify both files maintain their original encodings
        with open(path1, 'rb') as f:
            content1 = f.read()
        with open(path2, 'rb') as f:
            content2 = f.read()

        # CP1251 file should be decodable with CP1251
        try:
            decoded1 = content1.decode('cp1251')
            assert 'Измененный текст в CP1251' in decoded1
        except UnicodeDecodeError:
            pytest.fail('CP1251 file was not saved with the correct encoding')

        # UTF-8 file should be decodable with UTF-8
        try:
            decoded2 = content2.decode('utf-8')
            assert 'Измененный текст в UTF-8' in decoded2
        except UnicodeDecodeError:
            pytest.fail('UTF-8 file was not saved with the correct encoding')

    finally:
        # Clean up
        try:
            os.unlink(path1)
            os.unlink(path2)
        except FileNotFoundError:
            pass
