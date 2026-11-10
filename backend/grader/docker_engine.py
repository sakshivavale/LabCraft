"""
grader/docker_engine.py

Isolated Docker Sandbox Execution Service for LabCraft.

Why Docker for Code Execution?
  Running arbitrary code submitted by users on a server is an extreme security risk.
  Malicious or buggy code could:
    - Delete system files (`os.system("rm -rf /")`)
    - Exhaust server memory or CPU (infinite loops, fork bombs)
    - Open network sockets or attack other servers
    - Read sensitive environment variables (.env, passwords, database credentials)

  Docker containers provide a lightweight, isolated Linux namespace sandbox with:
    1. --network none         → Complete network isolation (no internet, no LAN).
    2. --memory=128m          → Memory quota (exceeding causes SIGKILL / OOM).
    3. --memory-swap=128m     → Disables swap space so memory limit is strict.
    4. --cpus=1.0             → CPU quota to prevent 100% CPU lockup.
    5. --pids-limit=64        → Process count limit (prevents fork bombs).
    6. --cap-drop ALL         → Drops all Linux kernel capabilities.
    7. --user 1000:1000       → Runs as unprivileged non-root user.
    8. --rm                   → Container is deleted immediately after execution.

Safety Rule:
  If the Docker daemon is unreachable or not installed, the engine MUST FAIL SAFELY.
  It must NEVER fall back to executing student code directly on the host system!
"""

import subprocess
import shutil
import tempfile
import os
import time
from typing import Tuple, Dict, Any, Optional


# =============================================================================
# LANGUAGE RUNTIME CONFIGURATIONS
# =============================================================================

LANGUAGE_CONFIGS = {
    'python': {
        'image': 'python:3.11-slim',
        'file_name': 'solution.py',
        'is_compiled': False,
        'run_cmd': ['python3', '-u', '/sandbox/solution.py'],
    },
    'c': {
        'image': 'gcc:latest',
        'file_name': 'solution.c',
        'is_compiled': True,
        'compile_cmd': ['gcc', '-O2', '/sandbox/solution.c', '-o', '/sandbox/solution'],
        'run_cmd': ['/sandbox/solution'],
    },
    'cpp': {
        'image': 'gcc:latest',
        'file_name': 'solution.cpp',
        'is_compiled': True,
        'compile_cmd': ['g++', '-O2', '/sandbox/solution.cpp', '-o', '/sandbox/solution'],
        'run_cmd': ['/sandbox/solution'],
    },
    'java': {
        'image': 'openjdk:17-slim',
        'file_name': 'Solution.java',
        'is_compiled': True,
        'compile_cmd': ['javac', '/sandbox/Solution.java'],
        'run_cmd': ['java', '-cp', '/sandbox', 'Solution'],
    },
    'javascript': {
        'image': 'node:18-alpine',
        'file_name': 'solution.js',
        'is_compiled': False,
        'run_cmd': ['node', '/sandbox/solution.js'],
    },
    'other': {
        'image': 'python:3.11-slim',
        'file_name': 'solution.py',
        'is_compiled': False,
        'run_cmd': ['python3', '-u', '/sandbox/solution.py'],
    },
}


# =============================================================================
# DOCKER AVAILABILITY CHECK
# =============================================================================

def is_docker_available() -> Tuple[bool, str]:
    """
    Checks if the Docker CLI is installed and the Docker daemon is running.

    Returns:
      (is_available: bool, message: str)
    """
    # 1. Check if 'docker' executable exists in system PATH
    docker_path = shutil.which('docker')
    if not docker_path:
        return False, (
            "Docker CLI is not installed or not found in system PATH. "
            "For security, student code is never executed directly on the host machine."
        )

    # 2. Check if the Docker daemon is running by querying 'docker info'
    try:
        result = subprocess.run(
            ['docker', 'info'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=3.0
        )
        if result.returncode != 0:
            return False, (
                "Docker daemon is not running or unreachable. "
                "For security, student code is never executed directly on the host machine."
            )
        return True, "Docker sandbox is available."
    except (subprocess.TimeoutExpired, Exception) as exc:
        return False, f"Docker daemon check failed: {str(exc)}"


# =============================================================================
# SANDBOX EXECUTION RESULT CLASS
# =============================================================================

class ExecutionResult:
    """Encapsulates the raw result of a container run."""
    def __init__(
        self,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        time_taken: float = 0.0,
        timed_out: bool = False,
        out_of_memory: bool = False,
        error_message: str = ""
    ):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.time_taken = time_taken
        self.timed_out = timed_out
        self.out_of_memory = out_of_memory
        self.error_message = error_message


# =============================================================================
# DOCKER EXECUTION SERVICE
# =============================================================================

class DockerSandbox:
    """
    Executes student code inside an ephemeral, locked-down Docker container.
    """

    def __init__(self, submission_code: str, language: str):
        self.code = submission_code
        self.language = language.lower()
        self.config = LANGUAGE_CONFIGS.get(self.language, LANGUAGE_CONFIGS['other'])

    def compile(self, temp_dir: str) -> Tuple[bool, str]:
        """
        Compiles the source code if the language requires compilation (C, C++, Java).

        Returns:
          (success: bool, error_output: str)
        """
        if not self.config.get('is_compiled', False):
            return True, ""  # Interpreted languages (Python, JS) require no compilation

        compile_cmd = self.config['compile_cmd']
        image = self.config['image']

        # Run compilation in a throwaway container
        docker_cmd = [
            'docker', 'run', '--rm',
            '--network', 'none',            # No network during compilation
            '--memory', '256m',             # Generous memory for compiler
            '--cpus', '1.0',                # 1 CPU
            '-v', f"{temp_dir}:/sandbox",   # Mount working dir
            '-w', '/sandbox',
            image
        ] + compile_cmd

        try:
            res = subprocess.run(
                docker_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15.0  # 15 seconds max compilation time
            )

            if res.returncode != 0:
                # Compilation failed — combine stderr and stdout for feedback
                err = (res.stderr or res.stdout).strip()
                return False, err
            return True, ""

        except subprocess.TimeoutExpired:
            return False, "Compilation timed out after 15 seconds."
        except Exception as exc:
            return False, f"Compilation setup error: {str(exc)}"

    def run_test_case(
        self,
        temp_dir: str,
        input_data: str,
        time_limit: float = 2.0,
        memory_limit: str = '128m'
    ) -> ExecutionResult:
        """
        Runs the compiled/interpreted program with a specific input_data string.

        Enforces strict safety constraints:
          - --network none: no networking
          - --memory: limit memory (e.g. 128m)
          - --memory-swap: disable swap
          - --pids-limit: max 64 processes
          - --user: non-root
          - timeout: enforced by subprocess.run
        """
        run_cmd = self.config['run_cmd']
        image = self.config['image']

        docker_cmd = [
            'docker', 'run', '--rm', '-i',
            '--network', 'none',
            '--memory', memory_limit,
            '--memory-swap', memory_limit,
            '--cpus', '1.0',
            '--pids-limit', '64',
            '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges',
            '-v', f"{temp_dir}:/sandbox:ro",  # Mount read-only for execution!
            '-w', '/sandbox',
            image
        ] + run_cmd

        start_time = time.time()

        try:
            proc = subprocess.run(
                docker_cmd,
                input=input_data,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=time_limit + 1.0  # Allow slight grace period for Docker startup overhead
            )

            elapsed = round(time.time() - start_time, 3)

            # Check for Docker OOM (exit code 137 typically denotes SIGKILL / OOM)
            is_oom = (proc.returncode == 137)

            return ExecutionResult(
                stdout=proc.stdout or "",
                stderr=proc.stderr or "",
                exit_code=proc.returncode,
                time_taken=elapsed,
                out_of_memory=is_oom,
            )

        except subprocess.TimeoutExpired:
            elapsed = round(time.time() - start_time, 3)
            return ExecutionResult(
                time_taken=elapsed,
                timed_out=True,
                error_message=f"Time Limit Exceeded ({time_limit}s)"
            )
        except Exception as exc:
            elapsed = round(time.time() - start_time, 3)
            return ExecutionResult(
                time_taken=elapsed,
                error_message=f"Sandbox error: {str(exc)}"
            )

