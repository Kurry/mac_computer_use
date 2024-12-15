"""Utility to run shell commands asynchronously with a timeout."""

import asyncio
import os
import signal

TRUNCATED_MESSAGE: str = (
    "<response clipped>"
    "<NOTE>To save on context only part of this file has been shown to you. "
    "You should retry this tool after you have searched inside the file with `grep -n` "
    "in order to find the line numbers of what you are looking for.</NOTE>"
)
MAX_RESPONSE_LEN: int = 16000


def maybe_truncate(content: str, truncate_after: int | None = MAX_RESPONSE_LEN) -> str:
    """
    Truncate content and append a notice if content exceeds the specified length.
    
    Args:
        content (str): The content to potentially truncate.
        truncate_after (int | None): The maximum allowed length of the content.
        
    Returns:
        str: The original or truncated content with a notice appended if truncated.
    """
    return (
        content
        if not truncate_after or len(content) <= truncate_after
        else content[:truncate_after] + TRUNCATED_MESSAGE
    )


async def run(
    cmd: str,
    timeout: float | None = 120.0,  # seconds
    truncate_after: int | None = MAX_RESPONSE_LEN,
) -> tuple[int, str, str]:
    """
    Run a shell command asynchronously with a timeout.
    
    Args:
        cmd (str): The shell command to execute.
        timeout (float | None): The maximum time (in seconds) to allow the command to run.
        truncate_after (int | None): The maximum length of the output before truncation.
        
    Returns:
        tuple[int, str, str]: A tuple containing the return code, standard output, and standard error.
        
    Raises:
        TimeoutError: If the command execution exceeds the specified timeout.
    """
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        preexec_fn=os.setsid,  # Start a new session to manage process groups.
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return (
            process.returncode or 0,
            maybe_truncate(stdout.decode(), truncate_after=truncate_after),
            maybe_truncate(stderr.decode(), truncate_after=truncate_after),
        )
    except asyncio.TimeoutError as exc:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)  # Terminate the entire process group.
        except ProcessLookupError:
            pass  # Process already terminated.
        raise TimeoutError(
            f"Command '{cmd}' timed out after {timeout} seconds"
        ) from exc
