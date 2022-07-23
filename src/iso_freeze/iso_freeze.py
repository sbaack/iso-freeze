"""Use pip install --report flag to separate pinned requirements for
different optional dependencies (e.g. 'dev' and 'doc' requirements)."""

import argparse
import subprocess
import sys
import json
from typing import Optional, Union
from pathlib import Path

if sys.version_info >= (3, 11, 0):
    import tomllib
else:
    import tomli as tomllib  # type: ignore


def read_toml(
    toml_file: Path,
    optional_dependency: Optional[str] = None,
) -> list[str]:
    """Read TOML file and return list dependencies.

    Includes requirements for optional dependency if any has been specified.

    Keyword Arguments:
        toml_file -- Path to pyproject.toml file
        optional_dependency -- Optional dependency to include (default: None)

    Returns:
        List of dependency names (list[str])
    """
    with open(toml_file, "rb") as f:
        metadata = tomllib.load(f)
    if not metadata.get("project"):
        sys.exit("TOML file does not contain a 'project' section.")
    dependencies: list[str] = metadata["project"].get("dependencies")
    if optional_dependency:
        if not metadata["project"].get("optional-dependencies"):
            sys.exit("No optional dependencies defined in TOML file.")
        optional_dependency_reqs: Optional[list[str]] = (
            metadata["project"].get("optional-dependencies").get(optional_dependency)
        )
        if optional_dependency_reqs:
            dependencies.extend(optional_dependency_reqs)
        else:
            sys.exit(
                f"No optional dependency '{optional_dependency}' found in TOML file."
            )
    return dependencies


def build_pip_command(
    python_exec: Path,
    toml_dependencies: Optional[list[str]],
    requirements_in: Optional[Path],
    pip_args: Optional[list[str]],
) -> list[Union[str, Path]]:
    """Build pip command to to generate report.

    Arguments:
        python_exec -- Path to Python interpreter to use (Path)
        toml_dependencies -- TOML dependencies to install (Optional[list[str]])
        requirements_in -- Path to requirements file (Optional[Path])
        pip_args -- Arguments to be passed to pip install (Optional[list[str]])

    Returns:
        Pip command to pass to run_pip_report (list[Union[str, Path]])
    """
    pip_report_command: list[Union[str, Path]] = [
        "env",
        "PIP_REQUIRE_VIRTUALENV=false",
        python_exec,
        "-m",
        "pip",
        "install",
    ]
    # If pip_args have been provided, inject them after the 'install' keyword
    if pip_args:
        pip_report_command.extend(pip_args)
    # Add necessary flags for calling pip install report
    pip_report_command.extend(
        ["-q", "--dry-run", "--ignore-installed", "--report", "-"]
    )
    # Finally, either append dependencies from TOML file or '-r requirements-file'
    if toml_dependencies:
        pip_report_command.extend([dependency for dependency in toml_dependencies])
    elif requirements_in:
        pip_report_command.extend(["-r", requirements_in])
    return pip_report_command


def run_pip_report(
    pip_report_command: list[Union[Path, str]]
) -> Optional[list[dict[str]]]:
    """Capture pip install --report to generate pinned requirements.

    Arguments:
        pip_report_command -- Command for subprocess (list[Union[Path, str]])
    """
    try:
        pip_report_raw_output: bytes = subprocess.check_output(pip_report_command)
        pip_report = json.loads(pip_report_raw_output.decode("utf-8"))
        if pip_report.get("install"):
            return pip_report.get("install")
        else:
            return None
    except subprocess.CalledProcessError as error:
        error.output
        sys.exit()


def write_requirements_file(dependencies: list[dict[str]], output_file: Path) -> None:
    """Write requirements file.

    Display top level dependencies on top, similar to pip freeze -r requirements_file.

    Keyword Arguments:
        dependencies -- Dependencies listed in pip install --report (list[dict[str]])
        output_file -- Path to and name of requirements.txt file (Path)
    """
    # For easier formatting we create separate lists for top level requirements
    # and their dependencies
    top_level_requirements: list[str] = []
    dependency_requirements: list[Optional[str]] = []
    for package in dependencies:
        package_name: str = package["metadata"]["name"]
        package_version: str = package["metadata"]["version"]
        # If requested == True, the package is a top level requirement
        if package["requested"]:
            top_level_requirements.append(f"{package_name}=={package_version}")
        else:
            dependency_requirements.append(f"{package_name}=={package_version}")
    with open(output_file, "w") as f:
        # Sort pinned packages alphabetically before writing to file
        # (case-insensitively thanks to key=str.lower)
        top_level_requirements.sort(key=str.lower)
        f.write("# Top level requirements\n")
        f.writelines(f"{package}\n" for package in top_level_requirements)
        if dependency_requirements:
            dependency_requirements.sort(key=str.lower)
            f.write("# Dependencies of top level requirements\n")
            f.writelines(f"{package}\n" for package in dependency_requirements)


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
        'pip-args "--arg1 value --arg2 value"',
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


def validate_pip_version(python_exec: Path) -> bool:
    """Check if pip version is >= 22.2.

    Returns:
        True/False (bool)
    """
    try:
        pip_version_call: str = subprocess.check_output(
            [python_exec, "-m", "pip", "--version"], encoding="utf-8"
        )
        # Output of pip --version looks like this:
        # pip 22.2 from <path to pip> (<python version>)
        # To get version number, split this message on whitespace and pick list item 1.
        # To check against minimum version, turn the version number into a list of ints
        # (e.g. '[22, 2]' or '[21, 1, 2]')
        pip_version: list[int] = [
            int(number) for number in pip_version_call.split()[1].split(".")
        ]
        if pip_version >= [22, 2]:
            return True
        return False
    except subprocess.CalledProcessError as error:
        error.output
        sys.exit()


def main() -> None:
    arguments: argparse.Namespace = parse_args()
    if not validate_pip_version(arguments.python):
        sys.exit("pip >= 22.2 required. Please update pip and try again.")
    if arguments.file.suffix == ".toml":
        toml_dependencies: Optional[list[str]] = read_toml(
            toml_file=arguments.file, optional_dependency=arguments.dependency
        )
    else:
        toml_dependencies = None
    pip_report_command: list[Union[str, Path]] = build_pip_command(
        python_exec=arguments.python,
        toml_dependencies=toml_dependencies,
        requirements_in=arguments.file,
        pip_args=arguments.pip_args,
    )
    dependencies = run_pip_report(pip_report_command=pip_report_command)
    if dependencies:
        write_requirements_file(dependencies=dependencies, output_file=arguments.output)
    else:
        sys.exit("There are no dependencies to pin")
    print(f"Pinned specified requirements in {arguments.output}")


if __name__ == "__main__":
    main()
