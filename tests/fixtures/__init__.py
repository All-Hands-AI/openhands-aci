"""Test fixtures for openhands-aci."""

import os


def get_fixture_path(filename):
    """Get the absolute path to a fixture file."""
    return os.path.join(os.path.dirname(__file__), filename)


def get_fixture_content(filename):
    """Get the content of a fixture file."""
    with open(get_fixture_path(filename), 'r', encoding='utf-8') as f:
        return f.read()
