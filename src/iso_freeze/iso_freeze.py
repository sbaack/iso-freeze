"""Use pip install --report flag to separate pinned requirements for
different optional dependencies (e.g. 'dev' and 'doc' requirements)."""

import argparse
import subprocess
import sys
import json
from dataclasses import dataclass
from typing import Any, Optional, Union
from pathlib import Path

if sys.version_info >= (3, 11, 0):
    import tomllib
else:
    import tomli as tomllib  # type: ignore


@dataclass
class PyPackage:
    """Class to capture relevant information about Python packages."""

    name: str
    version: str
    requested: bool = False
    hash: Optional[str] = None


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


def build_pip_report_command(
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


def run_pip(command: list[Union[str, Path]], check_output: bool) -> Any:
    """Run specified pip command with subprocess and return results, if any.

    Arguments:
        command -- pip command to execute (list[Union[str, Path]])

    Keyword Arguments:
        check_output -- Whether to call subprocess.check_output (default: {False})

    Returns:
        Output of pip command, if any (Optional[Any])
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


def get_dependencies(
    pip_report_command: list[Union[Path, str]],
) -> Optional[list[PyPackage]]:
    """Capture pip install --report to generate pinned requirements.

    Arguments:
        pip_report_command -- Command for subprocess (list[Union[Path, str]])

    Returns:
        List of PyPackage objects containing infos to pin requirements (list[PyPackage])
    """
    pip_report: dict[str, Any] = json.loads(
        run_pip(command=pip_report_command, check_output=True)
    )
    if pip_report.get("install"):
        dependencies: list[PyPackage] = []
        for package in pip_report["install"]:
            dependencies.append(
                PyPackage(
                    name=package["metadata"]["name"],
                    version=package["metadata"]["version"],
                    requested=package["requested"],
                    # pip report provides hashes in the form 'sha256=<hash>', but pip
                    # install requires 'sha256:<hash>', so we replace '=' with ':'
                    hash=package["download_info"]["archive_info"]["hash"].replace(
                        "=", ":"
                    ),
                )
            )
        return dependencies
    else:
        return None


def get_installed_packages(python_exec: Path) -> list[PyPackage]:
    """Run pip list --format json and return packages.

    Returns:
        List of packages from current environment (list[PyPackage])
    """
    pip_list_output: list[dict[str, str]] = json.loads(
        run_pip(
            command=[
                python_exec,
                "-m",
                "pip",
                "list",
                "--format",
                "json",
                "--exclude-editable",
            ],
            check_output=True,
        )
    )
    installed_packages: list[PyPackage] = []
    for package in pip_list_output:
        installed_packages.append(
            PyPackage(name=package["name"], version=package["version"])
        )
    return installed_packages


def remove_additional_packages(
    installed_packages: list[PyPackage], to_install: list[PyPackage], python_exec: Path
) -> None:
    """Remove packages installed in environment but not included in pip install --report.

    Arguments:
        installed_packages -- List of packages installed in current environment
                              (list[PyPackage])
        to_install -- List of packages taken from pip install --report
        python_exec -- Path to Python executable (Path)
    """
    # Create two lists with packages names only for easy comparison
    installed_names_only: list[str] = [package.name for package in installed_packages]
    to_install_names_only: list[str] = [package.name for package in to_install]
    to_delete: list[str] = [
        package
        for package in installed_names_only
        if package not in to_install_names_only
        # Don't remove default packages
        if package not in ["pip", "setuptools"]
    ]
    if to_delete:
        run_pip(
            command=[python_exec, "-m", "pip", "uninstall", "-y", *to_delete],
            check_output=False,
        )


def install_pip_report_output(to_install: list[PyPackage], python_exec: Path) -> None:
    """Install packages with pinned versions from pip install --report output.

    Arguments:
        to_install -- List of packages taken from pip install --report
        python_exec -- Path to Python executable (Path)
    """
    # Create list in the format ["package1==versionX", "package2==versionY"]
    # from `pip install --report` and pass that to `pip install`
    pinned_versions: list[str] = [
        f"{package.name}=={package.version}" for package in to_install
    ]
    run_pip(
        command=[python_exec, "-m", "pip", "install", "--upgrade", *pinned_versions],
        check_output=False,
    )


def build_reqirements_file_contents(
    dependencies: list[PyPackage], hashes: bool
) -> None:
    """Build lists to be written to a requirements file.

    Display top level dependencies on top, similar to pip freeze -r requirements_file.

    Arguments:
        dependencies -- Dependencies listed in pip install --report (list[dict[str]])
        hashes -- Whether to include hashes (bool)

    Returns:
        Contents of requirements file (list[str])
    """
    # For easier formatting we create separate lists for top level requirements
    # and their dependencies
    top_level_requirements: list[str] = []
    dependency_requirements: list[str] = []
    for package in dependencies:
        pinned_format: str = f"{package.name}=={package.version}"
        if hashes:
            pinned_format += f" \\\n    --hash={package.hash}"
        # If requested == True, the package is a top level requirement
        if package.requested:
            top_level_requirements.append(pinned_format)
        else:
            dependency_requirements.append(pinned_format)
    # Sort pinned packages alphabetically before writing to file
    # (case-insensitively thanks to key=str.lower)
    top_level_requirements.sort(key=str.lower)
    # Combine lists and add comments
    requirements_file_content: list[str] = [
        "# Top level requirements",
        *top_level_requirements,
    ]
    if dependency_requirements:
        dependency_requirements.sort(key=str.lower)
        requirements_file_content.extend(
            ["# Dependencies of top level requirements", *dependency_requirements]
        )
    return requirements_file_content


def write_requirements_file(output_file: Path, file_contents: list[str]) -> None:
    """Write requirements file.

    Arguments:
        output_file -- Path to and name of requirements.txt file (Path)
        file_contents -- Contents to to written to a file (list[str])
    """
    with output_file.open(mode="w", encoding="utf=8") as f:
        f.writelines(f"{package}\n" for package in file_contents)


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


def validate_pip_version(python_exec: Path) -> bool:
    """Check if pip version is >= 22.2.

    Returns:
        True/False (bool)
    """
    pip_version_call: str = run_pip(
        command=[python_exec, "-m", "pip", "--version"], check_output=True
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
    pip_report_command: list[Union[str, Path]] = build_pip_report_command(
        python_exec=arguments.python,
        toml_dependencies=toml_dependencies,
        requirements_in=arguments.file,
        pip_args=arguments.pip_args,
    )
    dependencies: Optional[list[PyPackage]] = get_dependencies(
        pip_report_command=pip_report_command
    )
    if dependencies:
        if arguments.sync:
            remove_additional_packages(
                installed_packages=get_installed_packages(python_exec=arguments.python),
                to_install=dependencies,
                python_exec=arguments.python,
            )
            install_pip_report_output(
                to_install=dependencies,
                python_exec=arguments.python,
            )
        else:
            output_file_contents: list[str] = build_reqirements_file_contents(
                dependencies=dependencies, hashes=arguments.hashes
            )
            write_requirements_file(
                output_file=arguments.output, file_contents=output_file_contents
            )
            print(f"Pinned specified requirements in {arguments.output}")
    else:
        sys.exit("There are no dependencies to pin")


if __name__ == "__main__":
    main()
