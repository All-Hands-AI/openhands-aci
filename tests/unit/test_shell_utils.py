import subprocess
from unittest.mock import MagicMock, patch

import pytest

from openhands_aci.editor.config import MAX_RESPONSE_LEN_CHAR
from openhands_aci.editor.prompts import CONTENT_TRUNCATED_NOTICE
from openhands_aci.utils.shell import run_shell_cmd


def test_run_shell_cmd_success():
    """Test running a successful shell command."""
    cmd = "echo 'Hello, World!'"
    returncode, stdout, stderr = run_shell_cmd(cmd)

    assert returncode == 0
    assert stdout.strip() == 'Hello, World!'
    assert stderr == ''


@patch('subprocess.Popen')
def test_run_shell_cmd_timeout(mock_popen):
    """Test that a TimeoutError is raised if command times out."""
    mock_process = MagicMock()
    mock_process.communicate.side_effect = subprocess.TimeoutExpired(
        cmd='sleep 2', timeout=1
    )
    mock_popen.return_value = mock_process

    with pytest.raises(TimeoutError, match="Command 'sleep 2' timed out"):
        run_shell_cmd('sleep 2', timeout=1)


@patch('subprocess.Popen')
def test_run_shell_cmd_truncation(mock_popen):
    """Test that stdout and stderr are truncated correctly."""
    long_output = 'a' * (MAX_RESPONSE_LEN_CHAR + 10)
    mock_process = MagicMock()
    mock_process.communicate.return_value = (long_output, long_output)
    mock_process.returncode = 0
    mock_popen.return_value = mock_process

    returncode, stdout, stderr = run_shell_cmd('echo long_output')

    assert returncode == 0
    assert len(stdout) <= MAX_RESPONSE_LEN_CHAR + len(CONTENT_TRUNCATED_NOTICE)
    assert len(stderr) <= MAX_RESPONSE_LEN_CHAR + len(CONTENT_TRUNCATED_NOTICE)
