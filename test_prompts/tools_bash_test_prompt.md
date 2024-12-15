Run these bash commands and identify where your results do not match the expected results.

---

## **1. Successful Command Executions**

These commands are expected to execute successfully, returning a **return code of `0`** with appropriate `STDOUT` and **no `STDERR`**.

### **A. Simple Echo Command**

- **Command:**
  ```bash
  echo "Hello, World!"
  ```
  
- **Description:**
  Tests the ability to execute a basic command that should succeed and return standard output.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  Hello, World!
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **B. List Existing Directory Contents**

- **Command:**
  ```bash
  ls /tmp
  ```
  
- **Description:**
  Lists the contents of the `/tmp` directory, which typically exists on Unix-like systems.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (List of files and directories in /tmp)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **C. Print Current Working Directory**

- **Command:**
  ```bash
  pwd
  ```
  
- **Description:**
  Prints the current working directory.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  /current/working/directory/path
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

---

## **2. Failing Command Executions**

These commands are designed to **fail**, returning a **non-zero return code**. They help verify that `run.py` correctly captures failures.

### **A. Exit with Non-Zero Status**

- **Command:**
  ```bash
  exit 1
  ```
  
- **Description:**
  Forces the shell to exit with status `1`, indicating failure.

- **Expected Return Code:**
  ```
  1
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **B. List Non-Existent Directory**

- **Command:**
  ```bash
  ls /nonexistent_directory
  ```
  
- **Description:**
  Attempts to list a directory that does not exist, producing an error.

- **Expected Return Code:**
  ```
  2
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  ls: cannot access '/nonexistent_directory': No such file or directory
  ```

### **C. Invalid Command Execution**

- **Command:**
  ```bash
  invalid_command
  ```
  
- **Description:**
  Tries to execute a command that does not exist, resulting in an error.

- **Expected Return Code:**
  ```
  127
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  /bin/bash: invalid_command: command not found
  ```

---

## **3. Commands Producing Standard Error**

These commands are expected to execute but produce error messages, helping to test `STDERR` capture.

### **A. Grep with No Matches**

- **Command:**
  ```bash
  grep "nomatch" /etc/passwd
  ```
  
- **Description:**
  Searches for a string that likely doesn't exist in `/etc/passwd`, resulting in no matches but also no error.

- **Expected Return Code:**
  ```
  1
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **B. Attempt to Remove Non-Existent File**

- **Command:**
  ```bash
  rm /tmp/nonexistent_file
  ```
  
- **Description:**
  Tries to remove a file that does not exist, producing an error.

- **Expected Return Code:**
  ```
  1
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  rm: cannot remove '/tmp/nonexistent_file': No such file or directory
  ```

---

## **4. Commands with Large Output (Testing Truncation)**

These commands generate substantial output to test the **output truncation** functionality of `run.py`.

### **A. Generate Large Output with `yes` Command**

- **Command:**
  ```bash
  yes "This is a test." | head -n 1000000
  ```
  
- **Description:**
  Generates a million lines of "This is a test." to produce a large `STDOUT`.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  This is a test.
  This is a test.
  ...
  (Truncated after `MAX_RESPONSE_LEN` characters)
  <response clipped><NOTE>To save on context only part of this file has been shown to you. You should retry this tool after you have searched inside the file with `grep -n` in order to find the line numbers of what you are looking for.</NOTE>
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **B. List Root Directory with Extensive Content**

- **Command:**
  ```bash
  ls -R /usr > /dev/null
  ```
  
- **Description:**
  Recursively lists all files in `/usr` directory, redirecting output to `/dev/null` to simulate large output handling.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Empty, since output is redirected to /dev/null)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

*Note: While this command redirects `STDOUT` to `/dev/null`, it's included to demonstrate handling of commands that generate large outputs without displaying them.*

---

## **5. Commands That Hang (Testing Timeout Functionality)**

These commands are designed to **hang** or run longer than the specified timeout, ensuring that `run.py` correctly terminates them.

### **A. Sleep Command Exceeding Timeout**

- **Command:**
  ```bash
  sleep 10
  ```
  
- **Description:**
  Causes the shell to sleep for 10 seconds. If the timeout is set to less than 10 seconds, it should trigger a `TimeoutError`.

- **Expected Return Code:**
  ```
  (Not returned; `TimeoutError` is raised)
  ```
  
- **Expected STDOUT:**
  ```
  (Not returned)
  ```
  
- **Expected STDERR:**
  ```
  (Not returned)
  ```

### **B. Long-Running Loop**

- **Command:**
  ```bash
  while true; do echo "Running..."; sleep 1; done
  ```
  
- **Description:**
  Continuously prints "Running..." every second. Should be terminated when timeout is reached.

- **Expected Return Code:**
  ```
  (Not returned; `TimeoutError` is raised)
  ```
  
- **Expected STDOUT:**
  ```
  Running...
  Running...
  ...
  (Truncated after `MAX_RESPONSE_LEN` characters, if applicable)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

---

## **6. Chained Commands**

These commands execute multiple commands in sequence using `&&`, ensuring that each subsequent command runs only if the preceding one succeeds.

### **A. All Commands Succeed**

- **Command:**
  ```bash
  cd /tmp && echo "Changed directory successfully." && pwd
  ```
  
- **Description:**
  Changes to `/tmp` directory, prints a success message, and displays the current directory.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  Changed directory successfully.
  /tmp
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **B. Intermediate Command Fails**

- **Command:**
  ```bash
  cd /nonexistent_directory && echo "This should not run." && ls
  ```
  
- **Description:**
  Attempts to change to a non-existent directory. Subsequent commands should not execute.

- **Expected Return Code:**
  ```
  1
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  bash: cd: /nonexistent_directory: No such file or directory
  ```

### **C. Final Command Fails**

- **Command:**
  ```bash
  cd /tmp && invalid_command && echo "This should not run."
  ```
  
- **Description:**
  Changes to `/tmp` directory successfully, attempts to run an invalid command, and should not execute the final echo.

- **Expected Return Code:**
  ```
  127
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  bash: invalid_command: command not found
  ```

### **D. Combining Commands with Logical OR**

- **Command:**
  ```bash
  cd /nonexistent_directory || echo "Failed to change directory." && ls
  ```
  
- **Description:**
  Attempts to change to a non-existent directory. If it fails, it echoes a failure message and then lists `/tmp` directory (since `&& ls` is linked to the `echo` command).

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  Failed to change directory.
  (List of files in the current directory, assuming `echo` succeeded)
  ```
  
- **Expected STDERR:**
  ```
  bash: cd: /nonexistent_directory: No such file or directory
  ```

*Note: This demonstrates combining `&&` and `||` for more complex command flows.*

---

## **7. Invalid and Dangerous Commands (Testing Security and Error Handling)**

These commands help ensure that `run.py` handles invalid inputs gracefully and securely.

### **A. Shell Injection Attempt**

- **Command:**
  ```bash
  echo "Safe Input" && rm -rf /
  ```
  
- **Description:**
  Attempts to execute a malicious command (`rm -rf /`) after a safe `echo` command. This tests whether `run.py` can handle or prevent shell injection.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  Safe Input
  ```
  
- **Expected STDERR:**
  ```
  (Error message from `rm` command, but depending on permissions, it may fail to execute)
  ```

- **Security Note:**
  *Be cautious when executing commands constructed from user input to prevent shell injection vulnerabilities. Always sanitize inputs using utilities like `shlex.quote`.*

### **B. Command with Special Characters**

- **Command:**
  ```bash
  echo "Path: /usr/local/bin && ls" 
  ```
  
- **Description:**
  Tests how `run.py` handles commands containing special characters that could be interpreted by the shell.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  Path: /usr/local/bin && ls
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Note:**
  This command should **not** execute `ls` because it's within quotes. It ensures that `run.py` correctly passes the entire string as a single argument.

---

## **8. Commands with Environment Variables**

These commands test whether `run.py` correctly handles environment variables when executing subprocesses.

### **A. Command with Custom Environment Variable**

- **Command:**
  ```bash
  echo $MY_TEST_VAR
  ```
  
- **Description:**
  Prints the value of a custom environment variable `MY_TEST_VAR`.

- **Setup:**
  Before executing, set the environment variable in `run.py` using the `env_vars` parameter.

  ```python
  env_vars = {'MY_TEST_VAR': 'Environment Variable Test'}
  return_code, stdout, stderr = asyncio.run(run("echo $MY_TEST_VAR", timeout=5, env_vars=env_vars))
  print(stdout)  # Should print: Environment Variable Test
  ```
  
- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  Environment Variable Test
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **B. Command Using PATH Environment Variable**

- **Command:**
  ```bash
  echo $PATH
  ```
  
- **Description:**
  Prints the system's `PATH` environment variable.

- **Usage Example:**
  ```python
  return_code, stdout, stderr = asyncio.run(run("echo $PATH", timeout=5))
  print(stdout)  # Should print the PATH variable
  ```
  
- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  /usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

---

## **9. Commands with Redirection and Piping**

These commands test `run.py`'s ability to handle output redirection and command piping.

### **A. Redirecting STDOUT to a File**

- **Command:**
  ```bash
  echo "Redirected Output" > /tmp/test_output.txt
  ```
  
- **Description:**
  Redirects the output of `echo` to a file, testing file redirection handling.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Empty, as output is redirected to the file)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Post-Execution Check:**
  Verify that `/tmp/test_output.txt` contains "Redirected Output".

  ```python
  with open("/tmp/test_output.txt", "r") as file:
      content = file.read().strip()
      print(content)  # Should print: Redirected Output
  ```

### **B. Piping Commands**

- **Command:**
  ```bash
  echo -e "apple\nbanana\ncherry" | grep "banana"
  ```
  
- **Description:**
  Pipes the output of `echo` into `grep` to search for the string "banana".

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  banana
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **C. Combining Redirection and Piping**

- **Command:**
  ```bash
  ls /tmp | grep "nonexistent_pattern" > /tmp/grep_output.txt
  ```
  
- **Description:**
  Pipes the output of `ls /tmp` into `grep` searching for a non-existent pattern, then redirects the output to a file.

- **Expected Return Code:**
  ```
  1
  ```
  
- **Expected STDOUT:**
  ```
  (Empty, as output is redirected to the file)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Post-Execution Check:**
  Verify that `/tmp/grep_output.txt` is empty.

  ```python
  with open("/tmp/grep_output.txt", "r") as file:
      content = file.read().strip()
      print(content)  # Should print: (Empty)
  ```

---

## **10. Testing with Subshells and Complex Expressions**

These commands evaluate how well `run.py` handles more complex shell features like subshells.

### **A. Command with Subshell**

- **Command:**
  ```bash
  (echo "Inside Subshell" && pwd)
  ```
  
- **Description:**
  Executes commands within a subshell, printing a message and the current directory.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  Inside Subshell
  /current/working/directory/path
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **B. Nested Commands with Conditional Execution**

- **Command:**
  ```bash
  mkdir /tmp/test_dir && cd /tmp/test_dir && touch test_file.txt
  ```
  
- **Description:**
  Creates a new directory, changes into it, and creates a new file. Tests conditional execution and directory/file manipulation.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Empty, unless commands produce output)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Post-Execution Check:**
  Verify that `/tmp/test_dir/test_file.txt` exists.

  ```python
  import os
  
  file_exists = os.path.isfile("/tmp/test_dir/test_file.txt")
  print(file_exists)  # Should print: True
  ```

### **C. Command with Logical OR**

- **Command:**
  ```bash
  cd /nonexistent_directory || echo "Failed to change directory."
  ```
  
- **Description:**
  Attempts to change to a non-existent directory. If it fails, it echoes a failure message. Tests logical OR (`||`) usage.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  Failed to change directory.
  ```
  
- **Expected STDERR:**
  ```
  bash: cd: /nonexistent_directory: No such file or directory
  ```

---

## **11. Commands with Environment Variable Manipulation**

These commands test how `run.py` handles environment variables within subprocesses.

### **A. Export and Use Environment Variable**

- **Command:**
  ```bash
  export MY_VAR="Test Variable" && echo $MY_VAR
  ```
  
- **Description:**
  Sets an environment variable `MY_VAR` and then echoes its value.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  Test Variable
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **B. Unset and Use Environment Variable**

- **Command:**
  ```bash
  export MY_VAR="Test Variable" && unset MY_VAR && echo $MY_VAR
  ```
  
- **Description:**
  Sets and then unsets an environment variable `MY_VAR`, then attempts to echo its value, which should result in an empty output.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

---

## **12. Commands with Signal Handling**

These commands test how `run.py` handles subprocesses receiving signals, especially during timeouts.

### **A. Terminate Process Gracefully**

- **Command:**
  ```bash
  sleep 30
  ```
  
- **Description:**
  Initiates a sleep for 30 seconds. If the timeout is set to less than 30 seconds, `run.py` should terminate the process gracefully using `SIGTERM`.

- **Expected Behavior When Timeout is < 30s:**
  - **Return Code:** Not returned; `TimeoutError` is raised
  - **STDOUT:** (Empty)
  - **STDERR:** (Empty)

- **Usage Example:**
  ```python
  try:
      return_code, stdout, stderr = asyncio.run(run("sleep 30", timeout=5))
  except TimeoutError as te:
      print(te)  # Should indicate that the command timed out
  ```

### **B. Force Kill Process After Timeout**

- **Command:**
  ```bash
  sleep 30
  ```
  
- **Description:**
  Similar to the previous command but intended to test whether `run.py` can handle forcefully killing a process group if the subprocess does not terminate gracefully.

- **Expected Behavior When Timeout is < 30s:**
  - **Return Code:** Not returned; `TimeoutError` is raised
  - **STDOUT:** (Empty)
  - **STDERR:** (Empty)
  
- **Note:**
  *This test assumes that `run.py` is configured to send `SIGKILL` after `SIGTERM` if the process does not terminate. Adjust the implementation accordingly if necessary.*

---

## **13. Commands with File Operations**

These commands test `run.py`'s ability to handle file creation, deletion, and manipulation.

### **A. Create a New File**

- **Command:**
  ```bash
  touch /tmp/new_test_file.txt
  ```
  
- **Description:**
  Creates a new empty file in `/tmp` directory.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Post-Execution Check:**
  ```python
  import os
  
  file_exists = os.path.isfile("/tmp/new_test_file.txt")
  print(file_exists)  # Should print: True
  ```

### **B. Remove the Created File**

- **Command:**
  ```bash
  rm /tmp/new_test_file.txt
  ```
  
- **Description:**
  Removes the previously created file.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Post-Execution Check:**
  ```python
  file_exists = os.path.isfile("/tmp/new_test_file.txt")
  print(file_exists)  # Should print: False
  ```

### **C. Write to a File Using Redirection**

- **Command:**
  ```bash
  echo "Test Content" > /tmp/write_test.txt
  ```
  
- **Description:**
  Writes "Test Content" to a new file, testing output redirection.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Post-Execution Check:**
  ```python
  with open("/tmp/write_test.txt", "r") as file:
      content = file.read().strip()
      print(content)  # Should print: Test Content
  ```

### **D. Append to a File Using Redirection**

- **Command:**
  ```bash
  echo "Additional Content" >> /tmp/write_test.txt
  ```
  
- **Description:**
  Appends "Additional Content" to the existing file.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Post-Execution Check:**
  ```python
  with open("/tmp/write_test.txt", "r") as file:
      content = file.read().strip()
      print(content)  
      # Should print:
      # Test Content
      # Additional Content
  ```

---

## **14. Commands with Conditional Execution and Logical Operators**

These commands test `run.py`'s ability to handle complex logical structures in Bash commands.

### **A. Conditional Execution with `&&`**

- **Command:**
  ```bash
  mkdir /tmp/test_dir && cd /tmp/test_dir && touch test_file.txt
  ```
  
- **Description:**
  Creates a directory, changes into it, and creates a file. Each command executes only if the previous one succeeds.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Empty, unless commands produce output)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Post-Execution Check:**
  ```python
  import os
  
  directory_exists = os.path.isdir("/tmp/test_dir")
  file_exists = os.path.isfile("/tmp/test_dir/test_file.txt")
  print(directory_exists)  # Should print: True
  print(file_exists)       # Should print: True
  ```

### **B. Conditional Execution with `||`**

- **Command:**
  ```bash
  cd /nonexistent_dir || echo "Failed to change directory."
  ```
  
- **Description:**
  Attempts to change to a non-existent directory. If it fails, it echoes a failure message.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  Failed to change directory.
  ```
  
- **Expected STDERR:**
  ```
  bash: cd: /nonexistent_dir: No such file or directory
  ```

### **C. Combining `&&` and `||`**

- **Command:**
  ```bash
  cd /tmp/test_dir && ls || echo "Failed to list directory."
  ```
  
- **Description:**
  Changes to a directory and lists its contents. If `ls` fails, it echoes a failure message.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  test_file.txt
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

*Assuming `/tmp/test_dir` exists and contains `test_file.txt`.*

---

## **15. Commands with Subprocess Interactions**

These commands test `run.py`'s ability to handle subprocess interactions, such as sending input to a command.

### **A. Using `grep` with Piped Input**

- **Command:**
  ```bash
  echo -e "apple\nbanana\ncherry" | grep "banana"
  ```
  
- **Description:**
  Pipes multiple lines of text into `grep` to search for the string "banana".

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  banana
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **B. Interactive Command Simulation**

- **Command:**
  ```bash
  printf "y\n" | rm -i /tmp/test_file.txt
  ```
  
- **Description:**
  Simulates user input (`y`) to confirm the deletion of a file using the interactive `rm -i` command.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  rm: remove regular empty file '/tmp/test_file.txt'? y
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Post-Execution Check:**
  ```python
  import os
  
  file_exists = os.path.isfile("/tmp/test_file.txt")
  print(file_exists)  # Should print: False
  ```

*Note: Ensure that `/tmp/test_file.txt` exists before running this command.*

---

## **16. Commands with Background Processes**

These commands test how `run.py` handles subprocesses that spawn background processes.

### **A. Start a Background Sleep Process**

- **Command:**
  ```bash
  sleep 30 &
  ```
  
- **Description:**
  Initiates a sleep command in the background. Tests whether `run.py` can handle background processes without waiting for them to complete.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  [1] 12345  # Job number and PID
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Post-Execution Check:**
  ```python
  import os
  
  # Replace 12345 with the actual PID returned
  process_exists = os.path.exists(f"/proc/{12345}")  # On Unix-like systems
  print(process_exists)  # Should print: True (if process is still running)
  ```

*Note: Handling background processes may require additional logic in `run.py` to manage or track these processes.*

---

## **17. Commands with Quoted Arguments**

These commands test `run.py`'s ability to handle arguments with spaces and special characters by using proper quoting.

### **A. Echo with Spaces and Special Characters**

- **Command:**
  ```bash
  echo "This is a test with spaces and $pecial #Characters!"
  ```
  
- **Description:**
  Tests handling of quoted strings containing spaces, special characters, and variables.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  This is a test with spaces and $pecial #Characters!
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **B. Create a File with Spaces in Name**

- **Command:**
  ```bash
  touch "/tmp/test file with spaces.txt"
  ```
  
- **Description:**
  Creates a file with spaces in its name, testing the handling of quoted filenames.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

- **Post-Execution Check:**
  ```python
  import os
  
  file_exists = os.path.isfile("/tmp/test file with spaces.txt")
  print(file_exists)  # Should print: True
  ```

---

## **18. Testing Command Output Encoding**

These commands ensure that `run.py` correctly handles different text encodings in command outputs.

### **A. Output with UTF-8 Characters**

- **Command:**
  ```bash
  echo "Unicode Test: 測試"
  ```
  
- **Description:**
  Outputs a string containing Unicode characters to test encoding handling.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  Unicode Test: 測試
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

### **B. Binary Output Simulation**

- **Command:**
  ```bash
  head -c 10 /dev/urandom | hexdump
  ```
  
- **Description:**
  Generates binary data and pipes it through `hexdump` to display hexadecimal representation. Tests handling of non-textual data.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Hexadecimal output representing binary data)
  ```
  
- **Expected STDERR:**
  ```
  (Empty)
  ```

*Note: Binary data should be handled carefully to prevent encoding errors.*

---

## **19. Commands with Conditional Failures and Recovery**

These commands test the script's ability to handle failures and perform recovery or fallback actions.

### **A. Attempt to Remove a File and Ignore Errors**

- **Command:**
  ```bash
  rm /tmp/nonexistent_file 2>/dev/null || echo "File does not exist, proceeding."
  ```
  
- **Description:**
  Attempts to remove a non-existent file, suppresses the error, and echoes a message if removal fails.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  File does not exist, proceeding.
  ```
  
- **Expected STDERR:**
  ```
  (Empty, as errors are redirected to /dev/null)
  ```

### **B. Create Directory if It Doesn't Exist**

- **Command:**
  ```bash
  mkdir /tmp/new_directory || echo "Directory already exists."
  ```
  
- **Description:**
  Attempts to create a directory. If it already exists, echoes a message instead of failing.

- **Expected Return Code:**
  ```
  0
  ```
  
- **Expected STDOUT:**
  ```
  (Empty, if directory is created successfully)
  ```
  **OR**
  ```
  Directory already exists.
  ```
  
- **Expected STDERR:**
  ```
  (Empty, if directory exists and `mkdir` fails, the error is handled by `echo`)
  ```

---

## **20. Commands Involving User Permissions**

These commands test how `run.py` handles permission-related errors.

### **A. Access Restricted Directory**

- **Command:**
  ```bash
  ls /root
  ```
  
- **Description:**
  Attempts to list contents of `/root` directory, which typically requires superuser permissions.

- **Expected Return Code:**
  ```
  2
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  ls: cannot open directory '/root': Permission denied
  ```

### **B. Create File in Restricted Directory**

- **Command:**
  ```bash
  touch /root/test_file.txt
  ```
  
- **Description:**
  Attempts to create a file in `/root` directory without sufficient permissions.

- **Expected Return Code:**
  ```
  1
  ```
  
- **Expected STDOUT:**
  ```
  (Empty)
  ```
  
- **Expected STDERR:**
  ```
  touch: cannot touch '/root/test_file.txt': Permission denied
  ```

---

## **Summary of Test Commands**

| **Category**                              | **Command**                                                                 | **Description**                                                                                          | **Expected Return Code** | **Expected STDOUT**                                                        | **Expected STDERR**                                           |
|-------------------------------------------|-----------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------|--------------------------|---------------------------------------------------------------------------|---------------------------------------------------------------|
| **1. Successful Commands**               | `echo "Hello, World!"`                                                      | Simple echo to test basic command execution.                                                             | `0`                      | `Hello, World!`                                                            | *(Empty)*                                                     |
|                                           | `ls /tmp`                                                                   | Lists contents of `/tmp` directory.                                                                      | `0`                      | *(List of files/directories)*                                             | *(Empty)*                                                     |
|                                           | `pwd`                                                                       | Prints current working directory.                                                                        | `0`                      | `/current/working/directory/path`                                         | *(Empty)*                                                     |
| **2. Failing Commands**                  | `exit 1`                                                                    | Forces shell to exit with status `1`.                                                                     | `1`                      | *(Empty)*                                                                  | *(Empty)*                                                     |
|                                           | `ls /nonexistent_directory`                                                 | Attempts to list a non-existent directory.                                                                 | `2`                      | *(Empty)*                                                                  | `ls: cannot access '/nonexistent_directory': No such file...`   |
|                                           | `invalid_command`                                                           | Executes a non-existent command.                                                                          | `127`                    | *(Empty)*                                                                  | `/bin/bash: invalid_command: command not found`               |
| **3. Commands Producing STDERR**         | `grep "nomatch" /etc/passwd`                                                | Searches for a non-existent string in `/etc/passwd`.                                                     | `1`                      | *(Empty)*                                                                  | *(Empty)*                                                     |
|                                           | `rm /tmp/nonexistent_file`                                                  | Attempts to remove a non-existent file.                                                                    | `1`                      | *(Empty)*                                                                  | `rm: cannot remove '/tmp/nonexistent_file': No such file...`   |
| **4. Large Output Commands**             | `yes "This is a test." | head -n 1000000`                                       | Generates a million lines to test output truncation.                                                      | `0`                      | *(Truncated output)*                                                       | *(Empty)*                                                     |
|                                           | `ls -R /usr > /dev/null`                                                    | Recursively lists `/usr` contents, redirecting output to `/dev/null`.                                     | `0`                      | *(Empty)*                                                                  | *(Empty)*                                                     |
| **5. Commands That Hang (Timeouts)**     | `sleep 10`                                                                  | Sleeps for 10 seconds to test timeout functionality.                                                      | *(Not returned)*         | *(Empty)*                                                                  | *(Not returned)*                                             |
|                                           | `while true; do echo "Running..."; sleep 1; done`                           | Continuously prints "Running..." every second.                                                            | *(Not returned)*         | *(Repeated "Running..." lines, truncated)*                                | *(Empty)*                                                     |
| **6. Chained Commands**                  | `cd /tmp && echo "Changed directory." && pwd`                               | Changes directory, echoes a message, and prints the current directory.                                    | `0`                      | `Changed directory.\n/tmp`                                                 | *(Empty)*                                                     |
|                                           | `cd /nonexistent_dir && echo "This should not run." && ls`                  | Attempts to change to a non-existent directory; subsequent commands should not execute.                   | `1`                      | *(Empty)*                                                                  | `bash: cd: /nonexistent_dir: No such file or directory`        |
|                                           | `cd /tmp && invalid_command && echo "This should not run."`                  | Changes to `/tmp`, runs an invalid command, and attempts to echo a message if the invalid command fails. | `127`                    | *(Empty)*                                                                  | `bash: invalid_command: command not found`                     |
|                                           | `cd /nonexistent_directory || echo "Failed to change directory."`            | Attempts to change to a non-existent directory; echoes a failure message if it fails.                     | `0`                      | `Failed to change directory.`                                              | `bash: cd: /nonexistent_directory: No such file or directory`  |
| **7. Invalid and Dangerous Commands**     | `echo "Safe Input" && rm -rf /`                                             | Attempts to execute a dangerous command after a safe echo. Tests shell injection handling.                | `0`                      | `Safe Input`                                                               | *(Error from `rm`, likely permission denied)*                  |
|                                           | `echo "Path: /usr/local/bin && ls"`                                         | Echoes a string containing `&& ls` within quotes, ensuring it doesn't execute `ls`.                       | `0`                      | `Path: /usr/local/bin && ls`                                               | *(Empty)*                                                     |
| **8. Commands with Environment Variables**| `echo $MY_TEST_VAR`                                                         | Prints the value of a custom environment variable.                                                        | `0`                      | `Environment Variable Test`                                                | *(Empty)*                                                     |
|                                           | `echo $PATH`                                                                | Prints the system's PATH environment variable.                                                             | `0`                      | `/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin`                          | *(Empty)*                                                     |
| **9. Redirection and Piping**            | `echo "Redirected Output" > /tmp/test_output.txt`                           | Redirects echo output to a file.                                                                           | `0`                      | *(Empty)*                                                                  | *(Empty)*                                                     |
|                                           | `echo -e "apple\nbanana\ncherry" | grep "banana"`                        | Pipes multiple lines into grep to search for "banana".                                                    | `0`                      | `banana`                                                                   | *(Empty)*                                                     |
|                                           | `ls /tmp | grep "nonexistent_pattern" > /tmp/grep_output.txt`                | Pipes `ls` into `grep` searching for a non-existent pattern, redirecting output to a file.                 | `1`                      | *(Empty)*                                                                  | *(Empty, as output is redirected to file)*                     |
| **10. Subshells and Complex Expressions** | `(echo "Inside Subshell" && pwd)`                                           | Executes commands within a subshell, echoing a message and printing the directory.                        | `0`                      | `Inside Subshell\n/tmp`                                                   | *(Empty)*                                                     |
|                                           | `mkdir /tmp/test_dir && cd /tmp/test_dir && touch test_file.txt`          | Creates a directory, changes into it, and creates a file.                                                | `0`                      | *(Empty)*                                                                  | *(Empty)*                                                     |
|                                           | `cd /nonexistent_directory || echo "Failed to change directory."`           | Attempts to change to a non-existent directory; echoes a failure message if it fails.                      | `0`                      | `Failed to change directory.`                                              | `bash: cd: /nonexistent_directory: No such file or directory`  |
| **11. Environment Variable Manipulation** | `export MY_VAR="Test Variable" && echo $MY_VAR`                            | Sets an environment variable and echoes its value.                                                        | `0`                      | `Test Variable`                                                            | *(Empty)*                                                     |
|                                           | `export MY_VAR="Test Variable" && unset MY_VAR && echo $MY_VAR`            | Sets and then unsets an environment variable; echoes its (now empty) value.                               | `0`                      | *(Empty)*                                                                  | *(Empty)*                                                     |
| **12. Signal Handling**                  | `sleep 30`                                                                  | Sleeps for 30 seconds. If timeout < 30, `run.py` should terminate the process.                            | *(Not returned)*         | *(Empty)*                                                                  | *(Not returned)*                                             |
|                                           | `sleep 30`                                                                  | Similar to above; intended to test force kill after timeout if graceful termination fails.                | *(Not returned)*         | *(Empty)*                                                                  | *(Not returned)*                                             |
| **13. File Operations**                  | `touch /tmp/new_test_file.txt`                                              | Creates a new empty file.                                                                                  | `0`                      | *(Empty)*                                                                  | *(Empty)*                                                     |
|                                           | `rm /tmp/new_test_file.txt`                                                 | Removes the created file.                                                                                  | `0`                      | *(Empty)*                                                                  | *(Empty)*                                                     |
|                                           | `echo "Test Content" > /tmp/write_test.txt`                                 | Writes "Test Content" to a file.                                                                           | `0`                      | *(Empty)*                                                                  | *(Empty)*                                                     |
|                                           | `echo "Additional Content" >> /tmp/write_test.txt`                          | Appends "Additional Content" to the existing file.                                                         | `0`                      | *(Empty)*                                                                  | *(Empty)*                                                     |
| **14. Conditional Execution**            | `mkdir /tmp/test_dir && ls /tmp/test_dir`                                   | Creates a directory and lists its contents if creation succeeds.                                          | `0`                      | `test_file.txt`                                                            | *(Empty)*                                                     |
|                                           | `mkdir /nonexistent_dir && echo "This should not run." && ls`               | Attempts to create a non-existent directory; subsequent commands should not execute.                       | `1`                      | *(Empty)*                                                                  | `bash: mkdir: cannot create directory '/nonexistent_dir': No such file or directory` |
|                                           | `cd /tmp && invalid_command && echo "This should not run."`                  | Changes to `/tmp`, runs an invalid command, and attempts to echo a message if the invalid command fails.    | `127`                    | *(Empty)*                                                                  | `bash: invalid_command: command not found`                     |
|                                           | `cd /nonexistent_directory || echo "Failed to change directory."`            | Attempts to change to a non-existent directory; echoes a failure message if it fails.                       | `0`                      | `Failed to change directory.`                                              | `bash: cd: /nonexistent_directory: No such file or directory`  |
| **15. Subprocess Interactions**          | `echo -e "apple\nbanana\ncherry" | grep "banana"`                           | Pipes multiple lines into grep to search for "banana".                                                      | `0`                      | `banana`                                                                   | *(Empty)*                                                     |
|                                           | `printf "y\n" | rm -i /tmp/test_file.txt`                                   | Simulates user input (`y`) to confirm file deletion using interactive `rm -i`.                             | `0`                      | `rm: remove regular empty file '/tmp/test_file.txt'? y`                   | *(Empty)*                                                     |
| **16. Background Processes**             | `sleep 30 &`                                                                | Starts a sleep command in the background.                                                                    | `0`                      | `[1] 12345` (Job number and PID)                                          | *(Empty)*                                                     |
| **17. Quoted Arguments**                 | `echo "This is a test with spaces and $pecial #Characters!"`                 | Echoes a string with spaces, special characters, and variables.                                             | `0`                      | `This is a test with spaces and $pecial #Characters!`                     | *(Empty)*                                                     |
|                                           | `touch "/tmp/test file with spaces.txt"`                                    | Creates a file with spaces in its name.                                                                     | `0`                      | *(Empty)*                                                                  | *(Empty)*                                                     |
| **18. Output Encoding**                  | `echo "Unicode Test: 測試"`                                                 | Echoes a string containing Unicode characters to test encoding handling.                                    | `0`                      | `Unicode Test: 測試`                                                        | *(Empty)*                                                     |
|                                           | `head -c 10 /dev/urandom | hexdump`                                      | Generates binary data and pipes it through `hexdump` to display hexadecimal representation.                  | `0`                      | `(Hexadecimal output)`                                                     | *(Empty)*                                                     |
| **19. Conditional Failures and Recovery**| `rm /tmp/nonexistent_file 2>/dev/null || echo "File does not exist, proceeding."` | Attempts to remove a non-existent file; suppresses error and echoes a message if removal fails.             | `0`                      | `File does not exist, proceeding.`                                         | *(Empty)*                                                     |
|                                           | `mkdir /tmp/new_directory || echo "Directory already exists."`               | Attempts to create a directory; echoes a message if it already exists.                                      | `0`                      | *(Empty)* or `Directory already exists.`                                 | *(Empty)*                                                     |
| **20. Encoding and Binary Output**       | `echo -e "apple\nbanana\ncherry" | grep "banana"`                           | Pipes multiple lines into grep to search for "banana".                                                      | `0`                      | `banana`                                                                   | *(Empty)*                                                     |
|                                           | `printf "y\n" | rm -i /tmp/test_file.txt`                                   | Simulates user input (`y`) to confirm file deletion using interactive `rm -i`.                             | `0`                      | `rm: remove regular empty file '/tmp/test_file.txt'? y`                   | *(Empty)*                                                     |

---
