from pathlib import Path

import pytest

from openhands_aci.editor.editor import OHEditor
from openhands_aci.editor.exceptions import (
    EditorToolParameterInvalidError,
    EditorToolParameterMissingError,
    EncodingError,
    ToolError,
)
from openhands_aci.editor.prompts import (
    DIRECTORY_CONTENT_TRUNCATED_NOTICE,
    FILE_CONTENT_TRUNCATED_NOTICE,
)
from openhands_aci.editor.results import CLIResult, ToolResult


@pytest.fixture
def editor(tmp_path):
    editor = OHEditor()
    # Set up a temporary directory with test files
    test_file = tmp_path / 'test.txt'
    test_file.write_text('This is a test file.\nThis file is for testing purposes.')
    return editor, test_file


@pytest.fixture
def editor_python_file_with_tabs(tmp_path):
    editor = OHEditor()
    # Set up a temporary directory with test files
    test_file = tmp_path / 'test.py'
    test_file.write_text('def test():\n\tprint("Hello, World!")')
    return editor, test_file


@pytest.fixture
def editor_cp1251_file(tmp_path):
    editor = OHEditor()
    # Set up a temporary directory with test files
    test_file = tmp_path / 'cp1251_file.py'

    # The exact content from the initial request
    content = """# coding: cp1251

from __future__ import absolute_import, print_function

import re
from datetime import datetime, date, time, timedelta

from pony.utils import is_ident

class ValidationError(ValueError):
    pass

def check_ip(s):
    s = s.strip()
    items = s.split('.')
    if len(items) != 4: raise ValueError()
    for item in items:
        if not 0 <= int(item) <= 255: raise ValueError()
    return s

def check_positive(s):
    i = int(s)
    if i > 0: return i
    raise ValueError()

def check_identifier(s):
    if is_ident(s): return s
    raise ValueError()

isbn_re = re.compile(r'(?:\\d[ -]?)+x?')

def isbn10_checksum(digits):
    if len(digits) != 9: raise ValueError()
    reminder = sum(digit*coef for digit, coef in zip(map(int, digits), range(10, 1, -1))) % 11
    if reminder == 1: return 'X'
    return reminder and str(11 - reminder) or '0'

def isbn13_checksum(digits):
    if len(digits) != 12: raise ValueError()
    reminder = sum(digit*coef for digit, coef in zip(map(int, digits), (1, 3)*6)) % 10
    return reminder and str(10 - reminder) or '0'

def check_isbn(s, convert_to=None):
    s = s.strip().upper()
    if s[:4] == 'ISBN': s = s[4:].lstrip()
    digits = s.replace('-', '').replace(' ', '')
    size = len(digits)
    if size == 10: checksum_func = isbn10_checksum
    elif size == 13: checksum_func = isbn13_checksum
    else: raise ValueError()
    digits, last = digits[:-1], digits[-1]
    if checksum_func(digits) != last:
        if last.isdigit() or size == 10 and last == 'X':
            raise ValidationError('Invalid ISBN checksum')
        raise ValueError()
    if convert_to is not None:
        if size == 10 and convert_to == 13:
            digits = '978' + digits
            s = digits + isbn13_checksum(digits)
        elif size == 13 and convert_to == 10 and digits[:3] == '978':
            digits = digits[3:]
            s = digits + isbn10_checksum(digits)
    return s

def isbn10_to_isbn13(s):
    return check_isbn(s, convert_to=13)

def isbn13_to_isbn10(s):
    return check_isbn(s, convert_to=10)

# The next two regular expressions taken from
# http://www.regular-expressions.info/email.html

email_re = re.compile(
    r'^[a-z0-9._%+-]+@[a-z0-9][a-z0-9-]*(?:\\.[a-z0-9][a-z0-9-]*)+$',
    re.IGNORECASE)

rfc2822_email_re = re.compile(r'''
    ^(?: [a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*
     |   "(?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21\\x23-\\x5b\\x5d-\\x7f]|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])*"
     )
     @
     (?: (?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?
     |   \\[ (?: (?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\\.){3}
            (?: 25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]
                :(?:[\\x01-\\x08\\x0b\\x0c\\x0e-\\x1f\\x21-\\x5a\\x53-\\x7f]|\\\\[\\x01-\\x09\\x0b\\x0c\\x0e-\\x7f])+
            )
         \\]
     )$''', re.IGNORECASE | re.VERBOSE)

def check_email(s):
    s = s.strip()
    if email_re.match(s) is None: raise ValueError()
    return s

def check_rfc2822_email(s):
    s = s.strip()
    if rfc2822_email_re.match(s) is None: raise ValueError()
    return s

date_str_list = [
    r'(?P<month>\\d{1,2})/(?P<day>\\d{1,2})/(?P<year>\\d{4})',
    r'(?P<day>\\d{1,2})\\.(?P<month>\\d{1,2})\\.(?P<year>\\d{4})',
    r'(?P<year>\\d{4})-(?P<month>\\d{1,2})-(?P<day>\\d{1,4})',
    r'(?P<year>\\d{4})/(?P<month>\\d{1,2})/(?P<day>\\d{1,4})',
    r'(?P<year>\\d{4})\\.(?P<month>\\d{1,2})\\.(?P<day>\\d{1,4})',
    r'\\D*(?P<year>\\d{4})\\D+(?P<day>\\d{1,2})\\D*',
    r'\\D*(?P<day>\\d{1,2})\\D+(?P<year>\\d{4})\\D*'
    ]
date_re_list = [ re.compile('^%s$'%s, re.UNICODE) for s in date_str_list ]

time_str = r'''
    (?P<hh>\\d{1,2})  # hours
    (?: \\s* [hu] \\s* )?  # optional hours suffix
    (?:
        (?: (?<=\\d)[:. ] | (?<!\\d) )  # separator between hours and minutes
        (?P<mm>\\d{1,2})  # minutes
        (?: (?: \\s* m(?:in)? | ' ) \\s* )?  # optional minutes suffix
        (?:
            (?: (?<=\\d)[:. ] | (?<!\\d) )  # separator between minutes and seconds
            (?P<ss>\\d{1,2}(?:\\.\\d{1,6})?)  # seconds with optional microseconds
            \\s*
            (?: (?: s(?:ec)? | " ) \\s* )?  # optional seconds suffix
        )?
    )?
    (?:  # optional A.M./P.M. part
        \\s* (?: (?P<am> a\\.?m\\.? ) | (?P<pm> p\\.?m\\.? ) )
    )?
'''
time_re = re.compile('^%s$'%time_str, re.VERBOSE)

datetime_re_list = [ re.compile('^%s(?:[t ]%s)?$' % (date_str, time_str), re.UNICODE | re.VERBOSE)
                     for date_str in date_str_list ]

month_lists = [
    "jan feb mar apr may jun jul aug sep oct nov dec".split(),
    u"янв фев мар апр май июн июл авг сен окт ноя дек".split(),  # Russian
    ]
month_dict = {}

for month_list in month_lists:
    for i, month in enumerate(month_list):
        month_dict[month] = i + 1

month_dict[u'май'] = 5  # Russian

def str2date(s):
    s = s.strip().lower()
    for date_re in date_re_list:
        match = date_re.match(s)
        if match is not None: break
    else: raise ValueError('Unrecognized date format')
    dict = match.groupdict()
    year = dict['year']
    day = dict['day']
    month = dict.get('month')
    if month is None:
        for key, value in month_dict.items():
            if key in s: month = value; break
        else: raise ValueError('Unrecognized date format')
    return date(int(year), int(month), int(day))

def str2time(s):
    s = s.strip().lower()
    match = time_re.match(s)
    if match is None: raise ValueError('Unrecognized time format')
    hh, mm, ss, mcs = _extract_time_parts(match.groupdict())
    return time(hh, mm, ss, mcs)

def str2datetime(s):
    s = s.strip().lower()
    for datetime_re in datetime_re_list:
        match = datetime_re.match(s)
        if match is not None: break
    else: raise ValueError('Unrecognized datetime format')

    d = match.groupdict()
    year, day, month = d['year'], d['day'], d.get('month')

    if month is None:
        for key, value in month_dict.items():
            if key in s: month = value; break
        else: raise ValueError('Unrecognized datetime format')

    hh, mm, ss, mcs = _extract_time_parts(d)
    return datetime(int(year), int(month), int(day), hh, mm, ss, mcs)

def _extract_time_parts(groupdict):
    hh, mm, ss, am, pm = map(groupdict.get, ('hh', 'mm', 'ss', 'am', 'pm'))

    if hh is None: hh, mm, ss = 12, 00, 00
    elif am and hh == '12': hh = 0
    elif pm and hh != '12': hh = int(hh) + 12

    if isinstance(ss, str) and '.' in ss:
        ss, mcs = ss.split('.', 1)
        if len('mcs') < 6: mcs = (mcs + '000000')[:6]
    else: mcs = 0

    return int(hh), int(mm or 0), int(ss or 0), int(mcs)

def str2timedelta(s):
    negative = s.startswith('-')
    if '.' in s:
        s, fractional = s.split('.')
        microseconds = int((fractional + '000000')[:6])
    else: microseconds = 0
    h, m, s = map(int, s.split(':'))
    td = timedelta(hours=abs(h), minutes=m, seconds=s, microseconds=microseconds)
    return -td if negative else td

def timedelta2str(td):
    total_seconds = td.days * (24 * 60 * 60) + td.seconds
    microseconds = td.microseconds
    if td.days < 0:
        total_seconds = abs(total_seconds)
        if microseconds:
            total_seconds -= 1
            microseconds = 1000000 - microseconds
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if microseconds: result = '%d:%d:%d.%06d' % (hours, minutes, seconds, microseconds)
    else: result = '%d:%d:%d' % (hours, minutes, seconds)
    if td.days >= 0: return result
    return '-' + result

converters = {
    int:  (int, str, 'Incorrect number'),
    float: (float, str, 'Must be a real number'),
    'IP': (check_ip, str, 'Incorrect IP address'),
    'positive': (check_positive, str, 'Must be a positive number'),
    'identifier': (check_identifier, str, 'Incorrect identifier'),
    'ISBN': (check_isbn, str, 'Incorrect ISBN'),
    'email': (check_email, str, 'Incorrect e-mail address'),
    'rfc2822_email': (check_rfc2822_email, str, 'Must be correct e-mail address'),
    date: (str2date, str, 'Must be correct date (mm/dd/yyyy or dd.mm.yyyy)'),
    time: (str2time, str, 'Must be correct time (hh:mm or hh:mm:ss)'),
    datetime: (str2datetime, str, 'Must be correct date & time'),
    }

def str2py(value, type):
    if type is None or not isinstance(value, str): return value
    if isinstance(type, tuple): str2py, py2str, err_msg = type
    else: str2py, py2str, err_msg = converters.get(type, (type, str, None))
    try: return str2py(value)
    except ValidationError: raise
    except:
        if value == '': return None
        raise ValidationError(err_msg or 'Incorrect data')"""

    # Write the file with cp1251 encoding
    with open(test_file, 'wb') as f:
        f.write(content.encode('cp1251'))

    return editor, test_file


def test_view_file(editor):
    editor, test_file = editor
    result = editor(command='view', path=str(test_file))
    assert isinstance(result, CLIResult)
    assert f"Here's the result of running `cat -n` on {test_file}:" in result.output
    assert '1\tThis is a test file.' in result.output
    assert '2\tThis file is for testing purposes.' in result.output


def test_view_directory(editor):
    editor, test_file = editor
    parent_dir = test_file.parent
    result = editor(command='view', path=str(parent_dir))
    assert (
        result.output
        == f"""Here's the files and directories up to 2 levels deep in {parent_dir}, excluding hidden items:
{parent_dir}/
{parent_dir}/test.txt"""
    )


def test_create_file(editor):
    editor, test_file = editor
    new_file = test_file.parent / 'new_file.txt'
    result = editor(command='create', path=str(new_file), file_text='New file content')
    assert isinstance(result, ToolResult)
    assert new_file.exists()
    assert new_file.read_text() == 'New file content'
    assert 'File created successfully' in result.output


def test_create_with_empty_string(editor):
    editor, test_file = editor
    new_file = test_file.parent / 'empty_content.txt'
    result = editor(command='create', path=str(new_file), file_text='')
    assert isinstance(result, ToolResult)
    assert new_file.exists()
    assert new_file.read_text() == ''
    assert 'File created successfully' in result.output


def test_create_with_none_file_text(editor):
    editor, test_file = editor
    new_file = test_file.parent / 'none_content.txt'
    with pytest.raises(EditorToolParameterMissingError) as exc_info:
        editor(command='create', path=str(new_file), file_text=None)
    assert 'file_text' in str(exc_info.value.message)


def test_str_replace_no_linting(editor):
    editor, test_file = editor
    result = editor(
        command='str_replace',
        path=str(test_file),
        old_str='test file',
        new_str='sample file',
    )
    assert isinstance(result, CLIResult)

    # Test str_replace command
    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of {test_file}:
     1\tThis is a sample file.
     2\tThis file is for testing purposes.
Review the changes and make sure they are as expected. Edit the file again if necessary."""
    )

    # Test that the file content has been updated
    assert 'This is a sample file.' in test_file.read_text()


def test_str_replace_multi_line_no_linting(editor):
    editor, test_file = editor
    result = editor(
        command='str_replace',
        path=str(test_file),
        old_str='This is a test file.\nThis file is for testing purposes.',
        new_str='This is a sample file.\nThis file is for testing purposes.',
    )
    assert isinstance(result, CLIResult)

    # Test str_replace command
    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of {test_file}:
     1\tThis is a sample file.
     2\tThis file is for testing purposes.
Review the changes and make sure they are as expected. Edit the file again if necessary."""
    )


def test_str_replace_multi_line_with_tabs_no_linting(editor_python_file_with_tabs):
    editor, test_file = editor_python_file_with_tabs
    result = editor(
        command='str_replace',
        path=str(test_file),
        old_str='def test():\n\tprint("Hello, World!")',
        new_str='def test():\n\tprint("Hello, Universe!")',
    )
    assert isinstance(result, CLIResult)

    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of {test_file}:
     1\tdef test():
     2\t{'\t'.expandtabs()}print("Hello, Universe!")
Review the changes and make sure they are as expected. Edit the file again if necessary."""
    )


def test_str_replace_with_linting(editor):
    editor, test_file = editor
    result = editor(
        command='str_replace',
        path=str(test_file),
        old_str='test file',
        new_str='sample file',
        enable_linting=True,
    )
    assert isinstance(result, CLIResult)

    # Test str_replace command
    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of {test_file}:
     1\tThis is a sample file.
     2\tThis file is for testing purposes.

No linting issues found in the changes.
Review the changes and make sure they are as expected. Edit the file again if necessary."""
    )

    # Test that the file content has been updated
    assert 'This is a sample file.' in test_file.read_text()


def test_str_replace_error_multiple_occurrences(editor):
    editor, test_file = editor
    with pytest.raises(ToolError) as exc_info:
        editor(
            command='str_replace', path=str(test_file), old_str='test', new_str='sample'
        )
    assert 'Multiple occurrences of old_str `test`' in str(exc_info.value.message)
    assert '[1, 2]' in str(exc_info.value.message)  # Should show both line numbers


def test_str_replace_error_multiple_multiline_occurrences(editor):
    editor, test_file = editor
    # Create a file with two identical multi-line blocks
    multi_block = """def example():
    print("Hello")
    return True"""
    content = f"{multi_block}\n\nprint('separator')\n\n{multi_block}"
    test_file.write_text(content)

    with pytest.raises(ToolError) as exc_info:
        editor(
            command='str_replace',
            path=str(test_file),
            old_str=multi_block,
            new_str='def new():\n    print("World")',
        )
    error_msg = str(exc_info.value.message)
    assert 'Multiple occurrences of old_str' in error_msg
    assert '[1, 7]' in error_msg  # Should show correct starting line numbers


def test_str_replace_nonexistent_string(editor):
    editor, test_file = editor
    with pytest.raises(ToolError) as exc_info:
        editor(
            command='str_replace',
            path=str(test_file),
            old_str='Non-existent Line',
            new_str='New Line',
        )
    assert 'No replacement was performed' in str(exc_info)
    assert f'old_str `Non-existent Line` did not appear verbatim in {test_file}' in str(
        exc_info.value.message
    )


def test_str_replace_with_empty_new_str(editor):
    editor, test_file = editor
    test_file.write_text('Line 1\nLine to remove\nLine 3')
    result = editor(
        command='str_replace',
        path=str(test_file),
        old_str='Line to remove\n',
        new_str='',
    )
    assert isinstance(result, CLIResult)
    assert test_file.read_text() == 'Line 1\nLine 3'


def test_str_replace_with_empty_old_str(editor):
    editor, test_file = editor
    test_file.write_text('Line 1\nLine 2\nLine 3')
    with pytest.raises(ToolError) as exc_info:
        editor(
            command='str_replace',
            path=str(test_file),
            old_str='',
            new_str='New string',
        )
    assert (
        str(exc_info.value.message)
        == """No replacement was performed. Multiple occurrences of old_str `` in lines [1, 2, 3]. Please ensure it is unique."""
    )


def test_str_replace_with_none_old_str(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterMissingError) as exc_info:
        editor(
            command='str_replace',
            path=str(test_file),
            old_str=None,
            new_str='new content',
        )
    assert 'old_str' in str(exc_info.value.message)


def test_insert_no_linting(editor):
    editor, test_file = editor
    result = editor(
        command='insert', path=str(test_file), insert_line=1, new_str='Inserted line'
    )
    assert isinstance(result, CLIResult)
    assert 'Inserted line' in test_file.read_text()
    print(result.output)
    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of the edited file:
     1\tThis is a test file.
     2\tInserted line
     3\tThis file is for testing purposes.
Review the changes and make sure they are as expected (correct indentation, no duplicate lines, etc). Edit the file again if necessary."""
    )


def test_insert_with_linting(editor):
    editor, test_file = editor
    result = editor(
        command='insert',
        path=str(test_file),
        insert_line=1,
        new_str='Inserted line',
        enable_linting=True,
    )
    assert isinstance(result, CLIResult)
    assert 'Inserted line' in test_file.read_text()
    print(result.output)
    assert (
        result.output
        == f"""The file {test_file} has been edited. Here's the result of running `cat -n` on a snippet of the edited file:
     1\tThis is a test file.
     2\tInserted line
     3\tThis file is for testing purposes.

No linting issues found in the changes.
Review the changes and make sure they are as expected (correct indentation, no duplicate lines, etc). Edit the file again if necessary."""
    )


def test_insert_invalid_line(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterInvalidError) as exc_info:
        editor(
            command='insert',
            path=str(test_file),
            insert_line=10,
            new_str='Invalid Insert',
        )
    assert 'Invalid `insert_line` parameter' in str(exc_info.value.message)
    assert 'It should be within the range of lines of the file' in str(
        exc_info.value.message
    )


def test_insert_with_empty_string(editor):
    editor, test_file = editor
    result = editor(
        command='insert',
        path=str(test_file),
        insert_line=1,
        new_str='',
    )
    assert isinstance(result, CLIResult)
    content = test_file.read_text().splitlines()
    assert '' in content
    assert len(content) == 3  # Original 2 lines plus empty line


def test_insert_with_none_new_str(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterMissingError) as exc_info:
        editor(
            command='insert',
            path=str(test_file),
            insert_line=1,
            new_str=None,
        )
    assert 'new_str' in str(exc_info.value.message)


def test_undo_edit(editor):
    editor, test_file = editor
    # Make an edit to be undone
    result = editor(
        command='str_replace',
        path=str(test_file),
        old_str='test file',
        new_str='sample file',
    )
    # Undo the edit
    result = editor(command='undo_edit', path=str(test_file))
    assert isinstance(result, CLIResult)
    assert 'Last edit to' in result.output
    assert 'test file' in test_file.read_text()  # Original content restored


def test_multiple_undo_edits(editor):
    editor, test_file = editor
    # Make an edit to be undone
    _ = editor(
        command='str_replace',
        path=str(test_file),
        old_str='test file',
        new_str='sample file v1',
    )
    # Make another edit to be undone
    _ = editor(
        command='str_replace',
        path=str(test_file),
        old_str='sample file v1',
        new_str='sample file v2',
    )
    # Undo the last edit
    result = editor(command='undo_edit', path=str(test_file))
    assert isinstance(result, CLIResult)
    assert 'Last edit to' in result.output
    assert 'sample file v1' in test_file.read_text()  # Previous content restored

    # Undo the first edit
    result = editor(command='undo_edit', path=str(test_file))
    assert isinstance(result, CLIResult)
    assert 'Last edit to' in result.output
    assert 'test file' in test_file.read_text()  # Original content restored


def test_validate_path_invalid(editor):
    editor, test_file = editor
    invalid_file = test_file.parent / 'nonexistent.txt'
    with pytest.raises(EditorToolParameterInvalidError):
        editor(command='view', path=str(invalid_file))


def test_create_existing_file_error(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterInvalidError):
        editor(command='create', path=str(test_file), file_text='New content')


def test_str_replace_missing_old_str(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterMissingError):
        editor(command='str_replace', path=str(test_file), new_str='sample')


def test_str_replace_new_str_and_old_str_same(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterInvalidError) as exc_info:
        editor(
            command='str_replace',
            path=str(test_file),
            old_str='test file',
            new_str='test file',
        )
    assert (
        'No replacement was performed. `new_str` and `old_str` must be different.'
        in str(exc_info.value.message)
    )


def test_insert_missing_line_param(editor):
    editor, test_file = editor
    with pytest.raises(EditorToolParameterMissingError):
        editor(command='insert', path=str(test_file), new_str='Missing insert line')


def test_undo_edit_no_history_error(editor):
    editor, test_file = editor
    empty_file = test_file.parent / 'empty.txt'
    empty_file.write_text('')
    with pytest.raises(ToolError):
        editor(command='undo_edit', path=str(empty_file))


def test_view_directory_with_hidden_files(tmp_path):
    editor = OHEditor()

    # Create a directory with some test files
    test_dir = tmp_path / 'test_dir'
    test_dir.mkdir()
    (test_dir / 'visible.txt').write_text('content1')
    (test_dir / '.hidden1').write_text('hidden1')
    (test_dir / '.hidden2').write_text('hidden2')

    # Create a hidden subdirectory with a file
    hidden_subdir = test_dir / '.hidden_dir'
    hidden_subdir.mkdir()
    (hidden_subdir / 'file.txt').write_text('content3')

    # Create a visible subdirectory
    visible_subdir = test_dir / 'visible_dir'
    visible_subdir.mkdir()

    # View the directory
    result = editor(command='view', path=str(test_dir))

    # Verify output
    assert isinstance(result, CLIResult)
    assert str(test_dir) in result.output
    assert 'visible.txt' in result.output  # Visible file is shown
    assert 'visible_dir' in result.output  # Visible directory is shown
    assert '.hidden1' not in result.output  # Hidden files not shown
    assert '.hidden2' not in result.output
    assert '.hidden_dir' not in result.output
    assert (
        '3 hidden files/directories in this directory are excluded' in result.output
    )  # Shows count of hidden items in current dir only
    assert 'ls -la' in result.output  # Shows command to view hidden files


def test_view_symlinked_directory(tmp_path):
    editor = OHEditor()

    # Create a directory with some test files
    source_dir = tmp_path / 'source_dir'
    source_dir.mkdir()
    (source_dir / 'file1.txt').write_text('content1')
    (source_dir / 'file2.txt').write_text('content2')

    # Create a subdirectory with a file
    subdir = source_dir / 'subdir'
    subdir.mkdir()
    (subdir / 'file3.txt').write_text('content3')

    # Create a symlink to the directory
    symlink_dir = tmp_path / 'symlink_dir'
    symlink_dir.symlink_to(source_dir)

    # View the symlinked directory
    result = editor(command='view', path=str(symlink_dir))

    # Verify that all files are listed through the symlink
    assert isinstance(result, CLIResult)
    assert str(symlink_dir) in result.output
    assert 'file1.txt' in result.output
    assert 'file2.txt' in result.output
    assert 'subdir' in result.output
    assert 'file3.txt' in result.output


def test_view_large_directory_with_truncation(editor, tmp_path):
    editor, _ = editor
    # Create a directory with many files to trigger truncation
    large_dir = tmp_path / 'large_dir'
    large_dir.mkdir()
    for i in range(1000):  # 1000 files should trigger truncation
        (large_dir / f'file_{i}.txt').write_text('content')

    result = editor(command='view', path=str(large_dir))
    assert isinstance(result, CLIResult)
    assert DIRECTORY_CONTENT_TRUNCATED_NOTICE in result.output


def test_view_directory_on_hidden_path(tmp_path):
    """Directory structure:
    .test_dir/
    ├── visible1.txt
    ├── .hidden1
    ├── visible_dir/
    │   ├── visible2.txt
    │   └── .hidden2
    └── .hidden_dir/
        ├── visible3.txt
        └── .hidden3
    """

    editor = OHEditor()

    # Create a directory with test files at depth 1
    hidden_test_dir = tmp_path / '.hidden_test_dir'
    hidden_test_dir.mkdir()
    (hidden_test_dir / 'visible1.txt').write_text('content1')
    (hidden_test_dir / '.hidden1').write_text('hidden1')

    # Create a visible subdirectory with visible and hidden files
    visible_subdir = hidden_test_dir / 'visible_dir'
    visible_subdir.mkdir()
    (visible_subdir / 'visible2.txt').write_text('content2')
    (visible_subdir / '.hidden2').write_text('hidden2')

    # Create a hidden subdirectory with visible and hidden files
    hidden_subdir = hidden_test_dir / '.hidden_dir'
    hidden_subdir.mkdir()
    (hidden_subdir / 'visible3.txt').write_text('content3')
    (hidden_subdir / '.hidden3').write_text('hidden3')

    # View the directory
    result = editor(command='view', path=str(hidden_test_dir))

    # Verify output
    assert isinstance(result, CLIResult)
    # Depth 1: Visible files/dirs shown, hidden files/dirs not shown
    assert 'visible1.txt' in result.output
    assert 'visible_dir' in result.output
    assert '.hidden1' not in result.output
    assert '.hidden_dir' not in result.output

    # Depth 2: Files in visible_dir shown
    assert 'visible2.txt' in result.output
    assert '.hidden2' not in result.output

    # Depth 2: Files in hidden_dir not shown
    assert 'visible3.txt' not in result.output
    assert '.hidden3' not in result.output

    # Hidden file count only includes depth 1
    assert (
        '2 hidden files/directories in this directory are excluded' in result.output
    )  # Only .hidden1 and .hidden_dir at depth 1


def test_view_large_file_with_truncation(editor, tmp_path):
    editor, _ = editor
    # Create a large file to trigger truncation
    large_file = tmp_path / 'large_test.txt'
    large_content = 'Line 1\n' * 16000  # 16000 lines should trigger truncation
    large_file.write_text(large_content)

    result = editor(command='view', path=str(large_file))
    assert isinstance(result, CLIResult)
    assert FILE_CONTENT_TRUNCATED_NOTICE in result.output


def test_validate_path_suggests_absolute_path(editor):
    editor, test_file = editor
    relative_path = test_file.name  # This is a relative path
    with pytest.raises(EditorToolParameterInvalidError) as exc_info:
        editor(command='view', path=relative_path)
    error_message = str(exc_info.value.message)
    assert 'The path should be an absolute path' in error_message
    assert 'Maybe you meant' in error_message
    suggested_path = error_message.split('Maybe you meant ')[1].strip('?')
    assert Path(suggested_path).is_absolute()


def test_non_utf8_encoding_error(tmp_path):
    """Test that files with non-UTF-8 encoding raise EncodingError."""
    editor = OHEditor()

    # Create a file with cp1251 encoding declaration
    cp1251_file = tmp_path / 'cp1251_file.py'

    # Create a file with non-UTF-8 content that's still valid text
    # We'll use cp1251 encoding for Russian text
    russian_text = '# coding: cp1251\n\n# Русский текст в кодировке cp1251'

    # Write the file with cp1251 encoding
    with open(cp1251_file, 'wb') as f:
        f.write(russian_text.encode('cp1251'))

    # Test view command
    with pytest.raises(EncodingError) as exc_info:
        editor(command='view', path=str(cp1251_file))
    assert 'The editor only supports UTF-8 encoding files' in str(exc_info.value)
    assert 'please use bash commands for files with other encoding' in str(
        exc_info.value
    )

    # Test str_replace command
    with pytest.raises(EncodingError) as exc_info:
        editor(
            command='str_replace',
            path=str(cp1251_file),
            old_str='import re',
            new_str='import re, sys',
        )
    assert 'The editor only supports UTF-8 encoding files' in str(exc_info.value)

    # Test insert command
    with pytest.raises(EncodingError) as exc_info:
        editor(
            command='insert', path=str(cp1251_file), insert_line=3, new_str='import sys'
        )
    assert 'The editor only supports UTF-8 encoding files' in str(exc_info.value)


def test_exact_cp1251_file_encoding_error(editor_cp1251_file):
    """Test that the exact cp1251 file from the initial request raises EncodingError."""
    editor, cp1251_file = editor_cp1251_file

    # Verify the file exists and has the expected encoding declaration
    with open(cp1251_file, 'rb') as f:
        first_line = f.readline().decode('cp1251')
        assert '# coding: cp1251' in first_line

    # Test view command
    with pytest.raises(EncodingError) as exc_info:
        editor(command='view', path=str(cp1251_file))
    assert 'The editor only supports UTF-8 encoding files' in str(exc_info.value)
    assert 'please use bash commands for files with other encoding' in str(
        exc_info.value
    )

    # Test str_replace command
    with pytest.raises(EncodingError) as exc_info:
        editor(
            command='str_replace',
            path=str(cp1251_file),
            old_str='import re',
            new_str='import re, sys',
        )
    assert 'The editor only supports UTF-8 encoding files' in str(exc_info.value)

    # Test insert command
    with pytest.raises(EncodingError) as exc_info:
        editor(
            command='insert', path=str(cp1251_file), insert_line=3, new_str='import sys'
        )
    assert 'The editor only supports UTF-8 encoding files' in str(exc_info.value)

    # Demonstrate how to read the file with bash commands
    # This is just to show that the file is valid and can be read with the right encoding
    import subprocess

    result = subprocess.run(['cat', str(cp1251_file)], capture_output=True)
    assert result.returncode == 0
    assert b'# coding: cp1251' in result.stdout
