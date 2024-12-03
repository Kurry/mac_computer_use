import asyncio
import pytest
import os
from .bash import _BashSession, ToolError

@pytest.fixture
async def bash_session():
    """Fixture to provide a bash session for tests."""
    session = _BashSession()
    await session.start()
    yield session
    session.stop()

@pytest.mark.asyncio
async def test_bash_immediate_false_timeout(bash_session):
    """
    Test that demonstrates a false positive timeout with a command that's 
    actually running but appears to timeout immediately.
    This reproduces the issue seen with gradle commands.
    """
    # Create a test script that simulates a long-running process
    script_path = '/tmp/test_long_running.sh'
    with open(script_path, 'w') as f:
        f.write('''#!/bin/bash
echo "Starting long process..."
for i in {1..10}; do
    sleep 1
    echo "Progress: $i/10"
done
echo "Done"
''')
    os.chmod(script_path, 0o755)

    # The script should take 10 seconds, but we'll see an immediate timeout
    # This demonstrates the false positive timeout issue
    with pytest.raises(ToolError) as exc_info:
        await bash_session.run(f"bash {script_path}")
    
    assert "timed out" in str(exc_info.value)
    
    # Verify the process is actually still running in the background
    ps_output = os.popen("ps aux | grep test_long_running.sh | grep -v grep").read()
    assert "test_long_running.sh" in ps_output, "Process should still be running"

@pytest.mark.asyncio
async def test_bash_missing_sentinel(bash_session):
    """
    Test that demonstrates how the sentinel issue causes timeouts.
    The command completes successfully but times out due to sentinel handling.
    """
    # Simple echo command that should work instantly
    command = 'echo "test output"'
    
    # This should complete immediately but will timeout
    # because the sentinel isn't properly handled
    with pytest.raises(ToolError) as exc_info:
        await bash_session.run(command)
    
    assert "timed out" in str(exc_info.value)

@pytest.mark.asyncio
async def test_bash_buffer_blocking(bash_session):
    """
    Test that demonstrates how buffer blocking causes perceived timeouts.
    Shows that the process is running but output handling causes issues.
    """
    # Create a command that produces output faster than it's read
    command = '''python3 -c "
import time
for i in range(1000):
    print(f'Line {i}' * 100)
    time.sleep(0.01)
"'''

    with pytest.raises(ToolError) as exc_info:
        await bash_session.run(command)
    
    assert "timed out" in str(exc_info.value)

@pytest.mark.asyncio
async def test_bash_gradlew_simulation(bash_session):
    """
    Test that simulates the gradle command behavior causing timeouts.
    This recreates the specific issue seen with gradle commands.
    """
    # Simulate gradle-like behavior with delayed startup and sporadic output
    command = '''python3 -c "
import time, sys
print('Initializing build...')
sys.stdout.flush()
time.sleep(2)  # Simulate gradle daemon startup
print('Starting build tasks...')
sys.stdout.flush()
time.sleep(1)  # Simulate task preparation
for i in range(5):
    print(f'Executing task {i}...')
    sys.stdout.flush()
    time.sleep(0.5)  # Simulate task execution
"'''

    with pytest.raises(ToolError) as exc_info:
        await bash_session.run(command)
    
    assert "timed out" in str(exc_info.value)