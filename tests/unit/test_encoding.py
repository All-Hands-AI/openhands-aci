"""Tests for handling different file encodings in the editor."""

import tempfile
from pathlib import Path

import pytest

from openhands_aci.editor.editor import OHEditor


class TestEncodingHandling:
    """Test suite for handling different file encodings in the editor."""

    @pytest.fixture
    def editor(self):
        """Create an editor instance for testing."""
        return OHEditor()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    def test_utf8_file(self, editor, temp_dir):
        """Test handling of UTF-8 encoded files."""
        # Create a UTF-8 file
        file_path = temp_dir / 'utf8_file.py'
        content = '# coding: utf-8\n\nprint("Hello, UTF-8! 你好, UTF-8!")\n'
        file_path.write_text(content, encoding='utf-8')

        # Test view command
        result = editor(command='view', path=str(file_path))
        assert 'Hello, UTF-8! 你好, UTF-8!' in result.output
        assert result.prev_exist is True

        # Test str_replace command
        result = editor(
            command='str_replace',
            path=str(file_path),
            old_str='print("Hello, UTF-8! 你好, UTF-8!")',
            new_str='print("Modified UTF-8! 修改的 UTF-8!")',
        )
        assert 'Modified UTF-8! 修改的 UTF-8!' in result.new_content

        # Verify the file content was correctly modified
        modified_content = file_path.read_text(encoding='utf-8')
        assert 'print("Modified UTF-8! 修改的 UTF-8!")' in modified_content
        assert '# coding: utf-8' in modified_content  # Encoding declaration preserved

    def test_cp1251_file(self, editor, temp_dir):
        """Test handling of CP1251 (Windows Cyrillic) encoded files."""
        # Create a CP1251 file
        file_path = temp_dir / 'cp1251_file.py'
        content = '# coding: cp1251\n\nprint("Привет, CP1251!")\n'
        file_path.write_text(content, encoding='cp1251')

        # Test view command
        result = editor(command='view', path=str(file_path))
        assert 'Привет, CP1251!' in result.output
        assert result.prev_exist is True

        # Test str_replace command
        result = editor(
            command='str_replace',
            path=str(file_path),
            old_str='print("Привет, CP1251!")',
            new_str='print("Изменено, CP1251!")',
        )
        assert 'Изменено, CP1251!' in result.new_content

        # Verify the file content was correctly modified
        modified_content = file_path.read_text(encoding='cp1251')
        assert 'print("Изменено, CP1251!")' in modified_content
        assert '# coding: cp1251' in modified_content  # Encoding declaration preserved

    def test_latin1_file(self, editor, temp_dir):
        """Test handling of Latin-1 (ISO-8859-1) encoded files."""
        # Create a Latin-1 file
        file_path = temp_dir / 'latin1_file.py'
        # Note: Latin-1 only supports characters up to 0xFF, so no Euro symbol
        content = '# coding: latin-1\n\nprint("Olá, Latin-1! ñ")\n'
        file_path.write_text(content, encoding='latin-1')

        # Test view command
        result = editor(command='view', path=str(file_path))
        assert 'Olá, Latin-1! ñ' in result.output
        assert result.prev_exist is True

        # Test str_replace command
        result = editor(
            command='str_replace',
            path=str(file_path),
            old_str='print("Olá, Latin-1! ñ")',
            new_str='print("¡Modificado, Latin-1! £")',
        )
        assert '¡Modificado, Latin-1! £' in result.new_content

        # Verify the file content was correctly modified
        modified_content = file_path.read_text(encoding='latin-1')
        assert 'print("¡Modificado, Latin-1! £")' in modified_content
        assert '# coding: latin-1' in modified_content  # Encoding declaration preserved

    def test_insert_command_with_encoding(self, editor, temp_dir):
        """Test insert command with different encodings."""
        # Create files with different encodings
        encodings = ['utf-8', 'cp1251', 'latin-1']

        for encoding in encodings:
            file_path = temp_dir / f'{encoding}_insert.py'

            # Create initial content with encoding declaration
            if encoding == 'utf-8':
                content = (
                    f'# coding: {encoding}\n\n# UTF-8 file with characters: 你好\n'
                )
            elif encoding == 'cp1251':
                content = (
                    f'# coding: {encoding}\n\n# CP1251 file with characters: Привет\n'
                )
            else:  # latin-1
                content = (
                    f'# coding: {encoding}\n\n# Latin-1 file with characters: Olá ñ\n'
                )

            file_path.write_text(content, encoding=encoding)

            # Test insert command
            new_content = f'# New line in {encoding} encoding\n'
            if encoding == 'utf-8':
                new_content += 'print("Inserted UTF-8 text: 你好")'
            elif encoding == 'cp1251':
                new_content += 'print("Inserted CP1251 text: Привет")'
            else:  # latin-1
                new_content += 'print("Inserted Latin-1 text: Olá ñ")'

            editor(
                command='insert',
                path=str(file_path),
                insert_line=3,  # Insert after the comment line
                new_str=new_content,
            )

            # Verify the file content was correctly modified
            modified_content = file_path.read_text(encoding=encoding)
            assert f'# New line in {encoding} encoding' in modified_content
            assert (
                f'# coding: {encoding}' in modified_content
            )  # Encoding declaration preserved

    def test_create_command_with_encoding_declaration(self, editor, temp_dir):
        """Test create command with encoding declarations."""
        # Test creating files with different encoding declarations
        encodings = ['utf-8', 'cp1251', 'latin-1']

        for encoding in encodings:
            file_path = temp_dir / f'created_{encoding}_file.py'

            # Create content with encoding declaration
            if encoding == 'utf-8':
                content = f'# coding: {encoding}\n\nprint("Created UTF-8 file: 你好")\n'
            elif encoding == 'cp1251':
                content = (
                    f'# coding: {encoding}\n\nprint("Created CP1251 file: Привет")\n'
                )
            else:  # latin-1
                content = (
                    f'# coding: {encoding}\n\nprint("Created Latin-1 file: Olá ñ")\n'
                )

            # Create the file
            result = editor(
                command='create',
                path=str(file_path),
                file_text=content,
            )

            # Verify the file was created with correct content
            assert not file_path.exists() or result.prev_exist is False

            # Read the file with the correct encoding
            created_content = file_path.read_text(encoding=encoding)
            assert f'# coding: {encoding}' in created_content

            # Test that we can view the file correctly
            view_result = editor(command='view', path=str(file_path))
            # Just check that the file was created and has the encoding declaration
            # The actual content may be displayed differently depending on the terminal's encoding
            assert f'# coding: {encoding}' in view_result.output

    def test_no_encoding_declaration(self, editor, temp_dir):
        """Test handling files without encoding declarations."""
        # Create a file without encoding declaration but with non-ASCII characters
        file_path = temp_dir / 'no_encoding_file.py'
        content = 'print("File without encoding declaration: é à ç")\n'
        file_path.write_text(content, encoding='utf-8')  # Default to UTF-8

        # Test view command
        result = editor(command='view', path=str(file_path))
        assert 'File without encoding declaration: é à ç' in result.output

        # Test str_replace command
        result = editor(
            command='str_replace',
            path=str(file_path),
            old_str='print("File without encoding declaration: é à ç")',
            new_str='print("Modified without declaration: ñ ü ö")',
        )
        assert 'Modified without declaration: ñ ü ö' in result.new_content

        # Verify the file content was correctly modified
        modified_content = file_path.read_text(encoding='utf-8')
        assert 'print("Modified without declaration: ñ ü ö")' in modified_content

    def test_fallback_to_utf8(self, editor, temp_dir):
        """Test fallback to UTF-8 when encoding declaration is incorrect."""
        # Create a file with incorrect encoding declaration
        file_path = temp_dir / 'wrong_encoding_file.py'
        # Use a simple ASCII file with a Latin-1 encoding declaration
        content = '# -*- coding: latin-1 -*-\n\nvalue = "test"\n'
        file_path.write_text(content, encoding='utf-8')

        # Test view command
        result = editor(command='view', path=str(file_path))
        # Check that the file was viewed successfully
        assert 'coding: latin-1' in result.output

        # Test str_replace command
        result = editor(
            command='str_replace',
            path=str(file_path),
            old_str='value = "test"',
            new_str='value = "modified"',
        )
        assert 'value = "modified"' in result.new_content

        # Verify the file content was correctly modified
        modified_content = file_path.read_text(encoding='utf-8')
        assert 'value = "modified"' in modified_content
        assert 'coding: latin-1' in modified_content  # Declaration preserved

        # Now test with UTF-8 content in a Latin-1 declared file
        # This should work because we fall back to UTF-8 when the encoding can't handle the content
        file_path = temp_dir / 'fallback_encoding_file.py'
        content = '# -*- coding: latin-1 -*-\n\nvalue = "test"\n'
        file_path.write_text(content, encoding='utf-8')

        # Modify the file to add UTF-8 content
        editor(
            command='str_replace',
            path=str(file_path),
            old_str='value = "test"',
            new_str='value = "UTF-8 content: 你好"',
        )

        # Verify the file content was correctly modified
        modified_content = file_path.read_text(encoding='utf-8')
        assert 'value = "UTF-8 content: 你好"' in modified_content
        assert 'coding: latin-1' in modified_content  # Declaration preserved
