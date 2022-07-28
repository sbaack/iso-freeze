"""Data structures and base functionality required across multiple modules."""

import subprocess
import sys

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union, Optional


@dataclass
class PyPackage:
    """Class to capture relevant information about Python packages."""

    name: str
    version: str
    requested: bool = False
    hash: Optional[str] = None


def run_pip(command: list[Union[str, Path]], check_output: bool) -> Any:
    """Run specified pip command with subprocess and return results, if any.

    Arguments:
        command -- pip command to execute (list[Union[str, Path]])

    Keyword Arguments:
        check_output -- Whether to call subprocess.check_output (default: {False})

    Returns:
        Output of pip command, if any (Any)
    """
    try:
        if check_output:
            return subprocess.check_output(command, encoding="utf-8")
        else:
            subprocess.run(command)
            return None
    except subprocess.CalledProcessError as error:
        error.output
        sys.exit()
