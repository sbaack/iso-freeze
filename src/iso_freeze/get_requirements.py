"""Getting requirements from pip install --report."""

import json
import sys

from pathlib import Path
from typing import Any, Union, Optional

if sys.version_info >= (3, 11, 0):
    import tomllib
else:
    import tomli as tomllib  # type: ignore

from iso_freeze.lib import PyPackage, run_pip


def get_pip_report_requirements(
    file: Path,
    python_exec: Path,
    pip_args: Optional[list[str]],
    optional_dependency: Optional[str],
) -> Optional[list[PyPackage]]:
    """Get dependencies to pass to pip install --report."""
    pip_report_command: list[Union[str, Path]] = build_pip_report_command(
        file=file,
        python_exec=python_exec,
        pip_args=pip_args,
        optional_dependency=optional_dependency,
    )
    pip_report: dict[str, Any] = get_pip_report(pip_report_command=pip_report_command)
    return read_pip_report(pip_report)


def build_pip_report_command(
    file: Path,
    python_exec: Path,
    pip_args: Optional[list[str]],
    optional_dependency: Optional[str]
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
    if file.suffix == ".toml":
        toml_dependencies = read_toml(
            toml_file=file, optional_dependency=optional_dependency
        )
        pip_report_command.extend([dependency for dependency in toml_dependencies])
    else:
        pip_report_command.extend(["-r", file])
    return pip_report_command


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


def get_pip_report(pip_report_command: list[Union[Path, str]]) -> dict[str, Any]:
    """Capture pip install --report output.

    Arguments:
        pip_report_command -- Command for subprocess (list[Union[Path, str]])

    Returns:
        Json pip report response (dict[str, Any])
    """
    return json.loads(run_pip(command=pip_report_command, check_output=True))


def read_pip_report(pip_report: dict[str, Any]) -> Optional[list[PyPackage]]:
    """Extract package names and versions from pip report.

    Arguments:
        pip_report_command -- Command for subprocess (list[Union[Path, str]])

    Returns:
        List of PyPackage objects containing infos to pin requirements (list[PyPackage])
    """
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
