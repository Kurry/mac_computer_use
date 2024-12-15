"""Utility to run shell commands asynchronously with a timeout.

This module provides an asynchronous interface to execute shell commands,
manage subprocesses, handle timeouts, and capture outputs. It is designed
to be portable across Unix-like systems, including macOS.

.. versionadded:: 1.0
"""

import asyncio
import os
import signal
import logging
from typing import Optional, Tuple

# Configure logging
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)  # Set to DEBUG for detailed logs; adjust as needed.


TRUNCATED_MESSAGE: str = (
    "<response clipped>"
    "<NOTE>To save on context only part of this file has been shown to you. "
    "You should retry this tool after you have searched inside the file with `grep -n` "
    "in order to find the line numbers of what you are looking for.</NOTE>"
)
MAX_RESPONSE_LEN: int = 16000


def maybe_truncate(content: str, truncate_after: Optional[int] = MAX_RESPONSE_LEN) -> str:
    """
    Truncate content and append a notice if content exceeds the specified length.

    Args:
        content (str): The content to potentially truncate.
        truncate_after (int | None): The maximum allowed length of the content.

    Returns:
        str: The original or truncated content with a notice appended if truncated.

    Raises:
        ValueError: If `truncate_after` is negative.
    """
    if truncate_after is not None and truncate_after < 0:
        raise ValueError("truncate_after must be non-negative or None.")

    if not truncate_after or len(content) <= truncate_after:
        logger.debug("Content within allowed length; no truncation needed.")
        return content
    truncated_content = content[:truncate_after] + TRUNCATED_MESSAGE
    logger.debug("Content truncated to %d characters.", truncate_after)
    return truncated_content


async def run(
    cmd: str,
    timeout: Optional[float] = 120.0,  # seconds
    truncate_after: Optional[int] = MAX_RESPONSE_LEN,
) -> Tuple[int, str, str]:
    """
    Run a shell command asynchronously with a timeout.

    This function executes a shell command in a new subprocess, captures its
    standard output and standard error, and enforces a timeout. If the command
    does not complete within the specified timeout, it is terminated along with
    its entire process group to prevent orphaned subprocesses.

    **Platform Support:**
    
    - **macOS:** Fully supported. Utilizes `start_new_session=True` for process group management.
    - **Unix-like Systems (Linux, BSD):** Fully supported.
    - **Windows:** Supported when using `ProactorEventLoop`. Note that some signal behaviors may differ.

    **Security Warning:**
    
    Be cautious when constructing shell commands from user input to prevent
    shell injection vulnerabilities. Use utilities like `shlex.quote` to safely
    escape user-provided strings.

    Args:
        cmd (str): The shell command to execute.
        timeout (float | None): The maximum time (in seconds) to allow the command to run.
                                 If `None`, waits indefinitely.
        truncate_after (int | None): The maximum length of the output before truncation.
                                     If `None`, does not truncate.

    Returns:
        tuple[int, str, str]: A tuple containing the return code, standard output,
                              and standard error.

    Raises:
        TimeoutError: If the command execution exceeds the specified timeout.
        ValueError: If `truncate_after` is negative.
        Exception: Propagates any unexpected exceptions encountered during execution.

    **Examples:**

    Successful Command:
    
        >>> import asyncio
        >>> return_code, stdout, stderr = asyncio.run(run("echo 'Hello, World!'", timeout=5))
        >>> print(return_code)
        0
        >>> print(stdout)
        Hello, World!
        >>> print(stderr)
    
    Failing Command:
    
        >>> return_code, stdout, stderr = asyncio.run(run("exit 1", timeout=5))
        >>> print(return_code)
        1
        >>> print(stdout)
        >>> print(stderr)
    
    Command That Times Out:
    
        >>> try:
        ...     return_code, stdout, stderr = asyncio.run(run("sleep 10", timeout=2))
        ... except TimeoutError as te:
        ...     print(te)
        ...
        Command 'sleep 10' timed out after 2 seconds
    
    Immediate Failure Due to Invalid Command:
    
        >>> return_code, stdout, stderr = asyncio.run(run("invalid_command", timeout=5))
        >>> print(return_code)
        127
        >>> print(stdout)
        >>> print(stderr)
        /bin/bash: invalid_command: command not found
    """
    logger.info("Executing command: %s", cmd)
    try:
        # Create the subprocess with a new session to manage process groups
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,  # Preferred over preexec_fn=os.setsid for better portability
        )
        logger.debug("Subprocess started with PID: %d", process.pid)

        try:
            # Wait for the subprocess to complete, with a timeout
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            logger.debug("Subprocess with PID %d completed.", process.pid)

            # Decode outputs
            stdout_decoded = stdout.decode().strip()
            stderr_decoded = stderr.decode().strip()

            # Truncate outputs if necessary
            stdout_truncated = maybe_truncate(stdout_decoded, truncate_after=truncate_after)
            stderr_truncated = maybe_truncate(stderr_decoded, truncate_after=truncate_after)

            logger.info("Command '%s' exited with return code %d.", cmd, process.returncode)
            return (process.returncode or 0, stdout_truncated, stderr_truncated)

        except asyncio.TimeoutError as timeout_exc:
            logger.warning("Command '%s' timed out after %.2f seconds.", cmd, timeout)
            try:
                # Terminate the entire process group
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                logger.debug("Sent SIGTERM to process group of PID %d.", process.pid)
            except ProcessLookupError:
                logger.error("Process group for PID %d does not exist or has already been terminated.", process.pid)
            except Exception as e:
                logger.exception("Failed to terminate process group for PID %d: %s", process.pid, e)

            raise TimeoutError(
                f"Command '{cmd}' timed out after {timeout} seconds"
            ) from timeout_exc

    except Exception as e:
        logger.exception("An error occurred while executing command '%s': %s", cmd, e)
        raise
