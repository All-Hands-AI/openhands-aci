import os
import tempfile
from pathlib import Path

import pytest

from openhands_aci.core.exceptions import ToolParameterInvalidError
from openhands_aci.navigator.navigator import SymbolNavigator


@pytest.fixture
def temp_git_repo():
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a git repo
        os.chdir(temp_dir)
        os.system('git init')
        os.system('git config user.name "test"')
        os.system('git config user.email "test@test.com"')

        # Create some Python files with known symbols
        # main.py defines MyClass and uses utils.helper_func
        main_content = """
from utils import helper_func

class MyClass:
    def __init__(self):
        self.value = 42

    def process(self):
        return helper_func(self.value)
"""
        Path('main.py').write_text(main_content)

        # utils.py defines helper_func and uses MyClass
        utils_content = """
from main import MyClass

def helper_func(x):
    obj = MyClass()
    return x + obj.value
"""
        Path('utils.py').write_text(utils_content)

        # Add files to git
        os.system('git add *.py')
        os.system('git commit -m "Initial commit"')

        yield temp_dir


def test_jump_to_definition_finds_class(temp_git_repo):
    navigator = SymbolNavigator()
    result = navigator(command='jump_to_definition', symbol_name='MyClass')

    assert 'Definition(s) of `MyClass`:' in result.output
    assert 'main.py:' in result.output
    assert 'class MyClass:' in result.output


def test_jump_to_definition_finds_function(temp_git_repo):
    navigator = SymbolNavigator()
    result = navigator(command='jump_to_definition', symbol_name='helper_func')

    assert 'Definition(s) of `helper_func`:' in result.output
    assert 'utils.py:' in result.output
    assert 'def helper_func(x):' in result.output


def test_find_references_finds_class_usages(temp_git_repo):
    navigator = SymbolNavigator()
    result = navigator(command='find_references', symbol_name='MyClass')

    assert 'References to `MyClass`:' in result.output
    assert 'utils.py:' in result.output
    assert 'obj = MyClass()' in result.output


def test_find_references_finds_function_usages(temp_git_repo):
    navigator = SymbolNavigator()
    result = navigator(command='find_references', symbol_name='helper_func')

    assert 'References to `helper_func`:' in result.output
    assert 'main.py:' in result.output
    assert 'return helper_func(self.value)' in result.output


def test_fuzzy_matching_for_nonexistent_symbol(temp_git_repo):
    navigator = SymbolNavigator()
    result = navigator(command='jump_to_definition', symbol_name='MyClss')  # Typo

    assert 'No definitions found for `MyClss`' in result.output
    assert 'Maybe you meant one of these:' in result.output
    assert 'MyClass' in result.output


def test_empty_symbol_raises_error(temp_git_repo):
    navigator = SymbolNavigator()
    with pytest.raises(ToolParameterInvalidError) as exc_info:
        navigator(command='jump_to_definition', symbol_name='')

    assert 'Symbol name cannot be empty' in str(exc_info.value)


def test_invalid_command_raises_error(temp_git_repo):
    navigator = SymbolNavigator()
    with pytest.raises(Exception) as exc_info:
        navigator(command='invalid_command', symbol_name='MyClass')

    assert 'Unrecognized command' in str(exc_info.value)
