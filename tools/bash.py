import asyncio
import os
from typing import ClassVar, Literal

from anthropic.types.beta import BetaToolBash20241022Param

from .base import BaseAnthropicTool, CLIResult, ToolError, ToolResult
from .run import run
from logger import logger


class _BashSession:
    """A session of a bash shell."""

    _started: bool
    _process: asyncio.subprocess.Process

    command: str = "/bin/bash"
    _output_delay: float = 0.2  # seconds
    _timeout: float = 120.0  # seconds
    _sentinel: str = "<<exit>>"

    def __init__(self):
        self._started = False
        self._timed_out = False

    async def start(self):
        if self._started:
            return

        self._process = await asyncio.create_subprocess_shell(
            self.command,
            preexec_fn=os.setsid,
            shell=True,
            bufsize=0,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        self._started = True

    def stop(self):
        """Terminate the bash shell."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return
        self._process.terminate()

    async def run(self, command: str):
        """Execute a command in the bash shell."""
        if not self._started:
            raise ToolError("Session has not started.")
        if self._process.returncode is not None:
            return ToolResult(
                system="tool must be restarted",
                error=f"bash has exited with returncode {self._process.returncode}",
            )
        if self._timed_out:
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            )

        # we know these are not None because we created the process with PIPEs
        assert self._process.stdin
        assert self._process.stdout
        assert self._process.stderr

        # send command to the process
        self._process.stdin.write(
            command.encode() + f"; echo '{self._sentinel}'\n".encode()
        )
        await self._process.stdin.drain()

        # read output from the process, until the sentinel is found
        try:
            async with asyncio.timeout(self._timeout):
                while True:
                    await asyncio.sleep(self._output_delay)
                    # if we read directly from stdout/stderr, it will wait forever for
                    # EOF. use the StreamReader buffer directly instead.
                    output = self._process.stdout._buffer.decode()  # pyright: ignore[reportAttributeAccessIssue]
                    if self._sentinel in output:
                        # strip the sentinel and break
                        output = output[: output.index(self._sentinel)]
                        break
        except asyncio.TimeoutError:
            self._timed_out = True
            raise ToolError(
                f"timed out: bash has not returned in {self._timeout} seconds and must be restarted",
            ) from None

        if output.endswith("\n"):
            output = output[:-1]

        error = self._process.stderr._buffer.decode()  # pyright: ignore[reportAttributeAccessIssue]
        if error.endswith("\n"):
            error = error[:-1]

        # clear the buffers so that the next output can be read correctly
        self._process.stdout._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]
        self._process.stderr._buffer.clear()  # pyright: ignore[reportAttributeAccessIssue]

        return CLIResult(output=output, error=error)


class BashTool(BaseAnthropicTool):
    """
    A tool that allows the agent to run bash commands.
    The tool parameters are defined by Anthropic and are not editable.
    """

    _session: _BashSession | None
    name: ClassVar[Literal["bash"]] = "bash"
    api_type: ClassVar[Literal["bash_20241022"]] = "bash_20241022"

    DEFAULT_TIMEOUT = 30.0  # Reduce from 120s to 30s
    MAX_RETRIES = 3

    def __init__(self):
        self._session = None
        super().__init__()

    async def __call__(
        self, command: str | None = None, restart: bool = False, **kwargs
    ):
        if restart:
            if self._session:
                self._session.stop()
            self._session = _BashSession()
            await self._session.start()

            return ToolResult(system="tool has been restarted.")

        if self._session is None:
            self._session = _BashSession()
            await self._session.start()

        if command is not None:
            return await self._session.run(command)

        raise ToolError("no command provided.")

    def to_params(self) -> BetaToolBash20241022Param:
        return {
            "type": self.api_type,
            "name": self.name,
        }

    async def run(self, command: str):
        """Run a bash command and return the output"""
        
        logger.debug(
            "",
            extra={
                'event_type': 'TOOL_USE',
                'sender': 'bash',
                'tool_name': 'bash',
                'command': command
            }
        )

        for attempt in range(self.MAX_RETRIES):
            try:
                # Run command with timeout
                _, stdout, stderr = await asyncio.wait_for(
                    run(command),
                    timeout=self.DEFAULT_TIMEOUT
                )
                
                # Log success
                logger.debug(
                    "",
                    extra={
                        'event_type': 'TOOL_RESULT',
                        'sender': 'bash',
                        'result_type': 'success',
                        'output': stdout if stdout else stderr
                    }
                )
                
                return ToolResult(output=stdout, error=stderr)

            except asyncio.TimeoutError:
                error_msg = f"Command timed out after {self.DEFAULT_TIMEOUT}s (attempt {attempt + 1}/{self.MAX_RETRIES})"
                logger.warning(error_msg)
                
                if attempt == self.MAX_RETRIES - 1:
                    # Log final failure
                    logger.error(
                        "",
                        extra={
                            'event_type': 'TOOL_RESULT', 
                            'sender': 'bash',
                            'result_type': 'error',
                            'error': error_msg
                        }
                    )
                    return ToolResult(error=error_msg)
                    
                # Kill any hanging processes before retry
                await run("pkill -f " + command.split()[0])
                await asyncio.sleep(1)  # Brief pause between retries
                
            except Exception as e:
                error_msg = f"Command failed: {str(e)}"
                logger.error(
                    "",
                    extra={
                        'event_type': 'TOOL_RESULT',
                        'sender': 'bash',
                        'result_type': 'error',
                        'error': error_msg
                    }
                )
                return ToolResult(error=error_msg)
