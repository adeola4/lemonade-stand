"""
Loop Master utilities.
"""

import subprocess
from typing import Optional


def run_cli(command: str, timeout: int = 60) -> str:
    """Run a CLI command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd="/home/ubuntu/.hermes/skills/tan-executive-agent"
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error: {str(e)}"
