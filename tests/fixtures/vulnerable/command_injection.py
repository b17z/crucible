# BAD: Command injection vulnerabilities
import os
import subprocess


def ping_host(hostname: str) -> str:
    """Ping a host - VULNERABLE to command injection."""
    # BAD: shell=True with user input
    result = subprocess.run(f"ping -c 1 {hostname}", shell=True, capture_output=True)
    return result.stdout.decode()


def read_file(filename: str) -> str:
    """Read a file - VULNERABLE to command injection."""
    # BAD: os.system with user input
    os.system(f"cat {filename}")
    return "done"


def list_directory(path: str) -> str:
    """List directory - VULNERABLE to command injection."""
    # BAD: Popen with shell=True
    proc = subprocess.Popen(f"ls -la {path}", shell=True, stdout=subprocess.PIPE)
    return proc.communicate()[0].decode()
