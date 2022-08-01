"""Use pip install --report flag to separate pinned requirements for
different optional dependencies (e.g. 'dev' and 'doc' requirements)."""

import argparse
import sys
from typing import Optional
from pathlib import Path

from iso_freeze.get_requirements import get_pip_report_requirements
from iso_freeze.lib import run_pip
from iso_freeze.sync import sync
from iso_freeze.pin_requirements import pin_requirements


def get_pip_version(python_exec: Path) -> str:
    """Return pip --version output.

    Returns:
        pip --version output (str)
    """
    return run_pip(command=[python_exec, "-m", "pip", "--version"], check_output=True)


def validate_pip_version(pip_version_output: str) -> bool:
    """Check if pip version is >= 22.2.

    Returns:
        True/False (bool)
    """
    # Output of pip --version looks like this:
    # "pip 22.2 from <path to pip> (<python version>)"
    # To get version number, split this message on whitespace and pick list item 1.
    # To check against minimum version, turn the version number into a list of ints
    # (e.g. '[22, 2]' or '[21, 1, 2]')
    pip_version: list[int] = [
        int(number) for number in pip_version_output.split()[1].split(".")
    ]
    if pip_version >= [22, 2]:
        return True
    return False


def determine_default_file() -> Optional[Path]:
    """Determine default input file if none has been specified.

    Returns:
        Path to default file (Optional[Path])
    """
    if Path("requirements.in").exists():
        default: Optional[Path] = Path("requirements.in")
    elif Path("pyproject.toml").exists():
        default = Path("pyproject.toml")
    else:
        default = None
    return default


def parse_args() -> argparse.Namespace:
    """Parse arguments."""
    argparser = argparse.ArgumentParser(
        description="Use pip install --report to cleanly separate pinned requirements "
        "for different optional dependencies (e.g. 'dev' and 'doc' requirements)."
    )
    argparser.add_argument(
        "file",
        type=Path,
        nargs="?",
        default=determine_default_file(),
        help="Path to input file. Can be pyproject.toml or requirements file. "
        "Defaults to 'requirements.in' or 'pyproject.toml' in current directory.",
    )
    argparser.add_argument(
        "--dependency",
        "-d",
        type=str,
        help="Name of the optional dependency defined in pyproject.toml to include.",
    )
    argparser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("requirements.txt"),
        help="Name of the output file. Defaults to 'requirements.txt' if unspecified.",
    )
    argparser.add_argument(
        "--python",
        "-p",
        type=Path,
        default=Path("python3"),
        help="Specify path to Python interpreter to use. Defaults to 'python3'.",
    )
    argparser.add_argument(
        "--pip-args",
        type=str,
        help="List of arguments to be passed to pip install. Call as: "
        'pip-args "--arg1 value --arg2 value".',
    )
    argparser.add_argument(
        "--sync",
        "-s",
        action="store_true",
        help="Sync current environment with dependencies listed in file (removes "
        "packages that are not dependencies in file, adds those that are missing)",
    )
    argparser.add_argument(
        "--hashes", action="store_true", help="Add hashes to output file."
    )
    args = argparser.parse_args()
    if not args.file:
        sys.exit(
            "No requirements.in or pyproject.toml file found in current directory. "
            "Please specify input file."
        )
    if args.file.suffix != ".toml" and args.dependency:
        sys.exit(
            "You can only specify an optional dependency if your input file is "
            "pyproject.toml."
        )
    if not args.file.is_file():
        sys.exit(f"Not a file: {args.file}")
    # If pip-args have been provided, split them into list
    if args.pip_args:
        args.pip_args = args.pip_args.split(" ")
    return args


def main() -> None:
    """ClI entry point."""
    arguments: argparse.Namespace = parse_args()
    if not validate_pip_version(pip_version_output=get_pip_version(arguments.python)):
        sys.exit("pip >= 22.2 required. Please update pip and try again.")
    pip_report_requirements = get_pip_report_requirements(
        file=arguments.file,
        python_exec=arguments.python,
        pip_args=arguments.pip_args,
        optional_dependency=arguments.dependency,
    )
    if pip_report_requirements:
        if arguments.sync:
            sync(requirements=pip_report_requirements, python_exec=arguments.python)
        else:
            pin_requirements(
                requirements=pip_report_requirements,
                hashes=arguments.hashes,
                output_file=arguments.output,
            )
    else:
        sys.exit("There are no requirements to pin.")


if __name__ == "__main__":
    main()
