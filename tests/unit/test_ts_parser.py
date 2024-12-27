import os
import tempfile

import pytest

from openhands_aci.tree_sitter.parser import TagKind, TreeSitterParser


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def parser(temp_dir):
    return TreeSitterParser(temp_dir)


def test_parse_python_function_definition(temp_dir, parser):
    # Create a temporary Python file with a function definition
    code = """def hello_world():
    print("Hello, World!")
    return 42

def another_func():
    result = hello_world()
    return result
"""
    file_path = os.path.join(temp_dir, 'test.py')
    with open(file_path, 'w') as f:
        f.write(code)

    tags = parser.get_tags_from_file(file_path, 'test.py')

    # Should find both function definitions and references
    def_tags = [t for t in tags if t.tag_kind == TagKind.DEF]
    ref_tags = [t for t in tags if t.tag_kind == TagKind.REF]
    def_with_body_tags = [t for t in tags if t.tag_kind == TagKind.DEF_WITH_BODY]

    assert len(def_tags) == 2  # hello_world and another_func
    assert len(ref_tags) >= 1  # At least hello_world reference
    assert len(def_with_body_tags) == 2

    # Verify specific references
    hello_world_refs = [t for t in ref_tags if t.node_content == 'hello_world']
    assert len(hello_world_refs) == 1

    # Check first function definition
    hello_def = next(t for t in def_tags if t.node_content == 'hello_world')
    assert hello_def.start_line == 0
    assert hello_def.end_line > 0  # Should be updated with body end line

    # Check function reference
    hello_ref = next(t for t in ref_tags if t.node_content == 'hello_world')
    assert hello_ref.start_line == 5


def test_parse_unsupported_file(temp_dir, parser):
    # Create a file with unsupported extension
    file_path = os.path.join(temp_dir, 'test.xyz')
    with open(file_path, 'w') as f:
        f.write('some content')

    tags = parser.get_tags_from_file(file_path, 'test.xyz')
    assert len(tags) == 0


def test_parse_empty_file(temp_dir, parser):
    # Create an empty Python file
    file_path = os.path.join(temp_dir, 'empty.py')
    with open(file_path, 'w') as f:
        f.write('')

    tags = parser.get_tags_from_file(file_path, 'empty.py')
    assert len(tags) == 0


def test_cache_functionality(temp_dir, parser):
    # Create a Python file
    file_path = os.path.join(temp_dir, 'cached.py')
    with open(file_path, 'w') as f:
        f.write('def test_func():\n    pass')

    # First call should parse the file
    tags1 = parser.get_tags_from_file(file_path, 'cached.py')
    assert len(tags1) > 0

    # Second call should use cache
    tags2 = parser.get_tags_from_file(file_path, 'cached.py')
    assert tags1 == tags2

    # Modify file should invalidate cache
    with open(file_path, 'w') as f:
        f.write('def another_func():\n    pass')

    # Use os.utime to explicitly set a new modification time
    import time

    new_time = time.time() + 1  # 1 second in the future
    os.utime(file_path, (new_time, new_time))

    tags3 = parser.get_tags_from_file(file_path, 'cached.py')

    # Compare the function names to verify cache invalidation
    func_names1 = {t.node_content for t in tags1 if t.tag_kind == TagKind.DEF}
    func_names3 = {t.node_content for t in tags3 if t.tag_kind == TagKind.DEF}
    assert func_names1 != func_names3


def test_parse_python_class_definition(temp_dir, parser):
    # Create a temporary Python file with a class definition
    code = """class TestClass:
    def method1(self):
        pass

    def method2(self):
        self.method1()
"""
    file_path = os.path.join(temp_dir, 'test_class.py')
    with open(file_path, 'w') as f:
        f.write(code)

    tags = parser.get_tags_from_file(file_path, 'test_class.py')

    def_tags = [t for t in tags if t.tag_kind == TagKind.DEF]
    ref_tags = [t for t in tags if t.tag_kind == TagKind.REF]

    # Should find class and both method definitions
    assert len(def_tags) >= 3
    # Should find the method1 reference
    assert len(ref_tags) >= 1

    # Verify class definition
    class_def = next(t for t in def_tags if t.node_content == 'TestClass')
    assert class_def.start_line == 0

    # Verify method reference
    method_ref = next(t for t in ref_tags if t.node_content == 'method1')
    assert method_ref.start_line == 5
