import subprocess
import time

from ..editor.config import MAX_RESPONSE_LEN_CHAR
from ..editor.results import maybe_truncate


def run_shell_cmd(
    cmd: str,
    timeout: float | None = 120.0,  # seconds
    truncate_after: int | None = MAX_RESPONSE_LEN_CHAR,
):
    """Run a shell command synchronously with a timeout."""
    start_time = time.time()

    try:
        process = subprocess.Popen(
            cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        stdout, stderr = process.communicate(timeout=timeout)

        return (
            process.returncode or 0,
            maybe_truncate(stdout, truncate_after=truncate_after),
            maybe_truncate(stderr, truncate_after=truncate_after),
        )
    except subprocess.TimeoutExpired:
        process.kill()
        elapsed_time = time.time() - start_time
        raise TimeoutError(
            f"Command '{cmd}' timed out after {elapsed_time:.2f} seconds"
        )
