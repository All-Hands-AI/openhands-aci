from openhands_aci.indexing.locagent.compress import get_skeleton


def test_get_skeleton_keeps_constants():
    code = '''
"""this is a module"""
const = {1,2,3}
import os
class fooClass:
    """this is a class"""
    def __init__(self, x):
        """initialization."""
        self.x = x
    def print(self):
        print(self.x)
def test():
    a = fooClass(3)
    a.print()
'''
    skeleton = get_skeleton(code, keep_constant=True)

    assert 'const = {1,2,3}' in skeleton
    assert 'class fooClass:' in skeleton
    assert 'def __init__' in skeleton
    assert 'def print' in skeleton
    assert 'def test' in skeleton
    assert '...' in skeleton  # ensure the body is replaced
