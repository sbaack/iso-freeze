"""Use new pip install --report flag to separate pinned requirements for
different optional dependencies (e.g. 'dev' and 'doc' requirements)."""

import argparse
import subprocess
import shutil
import sys
import json
from typing import Optional, Final, Union
from pathlib import Path

if sys.version_info >= (3, 11, 0):
    import tomllib
else:
    import tomli as tomllib  # type: ignore

TEMP_VENV: Final[Path] = Path(".iso-freeze-venv")
TEMP_VENV_EXEC: Final[Path] = Path(
    TEMP_VENV, *["Scripts" if sys.platform == "win32" else "bin"], "python"
)


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
        sys.exit("File does not contain a 'project' section")
    dependencies: list[str] = metadata["project"].get("dependencies")
    if optional_dependency:
        if metadata["project"].get("optional-dependencies"):
            optional_dependency_reqs: Optional[list[str]] = (
                metadata["project"]
                .get("optional-dependencies")
                .get(optional_dependency)
            )
            if optional_dependency_reqs:
                dependencies.extend(optional_dependency_reqs)
            else:
                sys.exit(
                    f"No optional dependency named {optional_dependency} found in your "
                    "pyproject.toml"
                )
        else:
            sys.exit("No optional dependencies defined in your pyproject.toml")
    return dependencies


def install_packages(
    dependencies: Optional[list[str]],
    requirements_in: Optional[Path],
    install_args: Optional[list[str]],
    verbose: bool,
) -> None:
    """Install packages listed in pyproject.toml or in a requirements file into
    temporary venv.

    Arguments:
        dependencies -- Names of dependencies to install (Optional[list[str]])
        requirements_in -- Path to requirements file (Optional[Path])
        install_args -- Arguments to be passed to pip install (Optional[list[str]])
        verbose -- Whether output of pip install is printed (bool)
    """
    pip_install_command: list[Union[Path, str]] = [
        TEMP_VENV_EXEC,
        "-m",
        "pip",
        "install",
        "--upgrade",
    ]
    # If install_args have been provided, inject them after the 'install' keyword
    if install_args:
        pip_install_command.extend(install_args)
    if not verbose:
        pip_install_command.extend(["-q"])
    # Finally, add commands to install either dependency list of requirements file
    if dependencies:
        pip_install_command.extend([dependency for dependency in dependencies])
    elif requirements_in:
        pip_install_command.extend(["-r", requirements_in])
    run_pip_install(pip_install_command=pip_install_command)


def run_pip_install(pip_install_command: list[Union[Path, str]]) -> None:
    """Run pip install.

    Arguments:
        pip_install_command -- Command for pip install (list[Union[Path, str]])
    """
    try:
        subprocess.run(pip_install_command, check=True)
    except subprocess.CalledProcessError as error:
        shutil.rmtree(TEMP_VENV)
        error.output
        sys.exit()


def create_venv(python_exec: Path) -> None:
    """Create temporary venv.

    Arguments:
        python_exec -- Path to Python interpreter to use (Path)
    """
    try:
        subprocess.run([python_exec, "-m", "venv", TEMP_VENV.name], check=True)
        # Quietly update pip to the latest version
        subprocess.run(
            [TEMP_VENV_EXEC, "-m", "pip", "install", "-q", "-U", "pip"], check=True
        )
    except subprocess.CalledProcessError as error:
        shutil.rmtree(TEMP_VENV)
        error.output
        sys.exit()


def freeze_packages(
    output_file: Path, input_file: Path, freeze_args: Optional[list[str]], verbose: bool
) -> None:
    """Create pinned requirements file.

    Arguments:
        output_file -- Path and name of output file (Path)
        input_file -- Path to input file (Path)
        freeze_args -- Arguments to be passed to pip freeze (Optional[list[str]])
        verbose -- Whether output of pip freeze is printed (bool)
    """
    pip_freeze_command: list[Union[Path, str]] = [
        TEMP_VENV_EXEC,
        "-m",
        "pip",
        "freeze",
    ]
    # If freeze_args have been provided, inject them after the 'freeze' keyword
    if freeze_args:
        pip_freeze_command.extend(freeze_args)
    # If input file is a requirements file, add "-r input_file" for nicer
    # requirements.txt format
    if input_file.suffix != ".toml":
        # Don't add "-r input_file" if the "--exclude <package>" option was provided
        # Otherwise "-r input_file" would negate "--exclude" if the excluded package
        # is listed in the input file
        if not freeze_args or "--exclude" not in freeze_args:
            pip_freeze_command.extend(["-r", input_file])
    run_pip_freeze(
        pip_freeze_command=pip_freeze_command, output_file=output_file, verbose=verbose
    )


def run_pip_freeze(
    pip_freeze_command: list[Union[Path, str]], output_file: Path, verbose: bool
) -> None:
    """Make subprocess call to pip freeze.

    Arguments:
        pip_freeze_command -- Command for pip freeze (list[Union[Path, str]])
        output_file -- Path to and name of requirements.txt file (Path)
        verbose -- Whether output of pip freeze is printed (bool)
    """
    pip_freeze_raw_output: bytes = subprocess.check_output(pip_freeze_command)
    if pip_freeze_raw_output:
        pip_freeze_output: str = pip_freeze_raw_output.decode("utf-8")
        output_file.write_text(pip_freeze_output)
        if verbose:
            print(f"\nPinned packages:\n{pip_freeze_output}")
    else:
        shutil.rmtree(TEMP_VENV)
        sys.exit("There are no dependencies to pin")


def pip222_pin(
    python_exec: Path,
    toml_dependencies: Optional[list[str]],
    requirements_in: Optional[Path],
    output_file: Path,
    install_args: Optional[list[str]],
) -> None:
    """Pin packages with --report flag introduced in pip 22.2."""
    pip_report_command: list[Union[str, Path]] = [
        "env",
        "PIP_REQUIRE_VIRTUALENV=false",
        python_exec,
        "-m",
        "pip",
        "install",
    ]
    # If install_args have been provided, inject them after the 'install' keyword
    if install_args:
        pip_report_command.extend(install_args)
    # Add necessary flags for calling pip install report
    pip_report_command.extend(
        ["-q", "--dry-run", "--ignore-installed", "--report", "-"]
    )
    # Finally, either append dependencies from TOML file or '-r requirements-file'
    if toml_dependencies:
        pip_report_command.extend([dependency for dependency in toml_dependencies])
    elif requirements_in:
        pip_report_command.extend(["-r", requirements_in])
    run_pip_report(pip_report_command, output_file)


def run_pip_report(
    pip_report_command: list[Union[Path, str]], output_file: Path
) -> None:
    """Run pip report and save output to file."""
    try:
        pip_report_raw_output: bytes = subprocess.check_output(pip_report_command)
        pip_report = json.loads(pip_report_raw_output.decode("utf-8"))
        if pip_report.get("install"):
            pinned_packages: Optional[list[str]] = []
            for package in pip_report.get("install"):
                package_name: str = package["metadata"]["name"]
                package_version: str = package["metadata"]["version"]
                pinned_packages.append(f"{package_name}=={package_version}")
            # Sort pinned packages alphabetically before writing to file
            pinned_packages.sort(key=str.lower)
            with open(output_file, "w") as f:
                f.writelines(f"{package}\n" for package in pinned_packages)
        else:
            sys.exit("There are no dependencies to pin")
    except subprocess.CalledProcessError as error:
        error.output
        sys.exit()


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
        "--install-args",
        type=str,
        help="List of arguments to be passed to pip install. Call as: "
        'install-args "--arg1 value --arg2 value"',
    )
    argparser.add_argument(
        "--freeze-args",
        type=str,
        help="List of arguments to be passed to pip freeze. Call as: "
        'freeze-args "--arg1 value --arg2 value"',
    )
    argparser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show all output from pip install and pip freeze (only applies "
        "when --venv flag is set).",
    )
    argparser.add_argument(
        "--venv",
        action="store_true",
        help="Resolve dependencies by installing them in isolated venv instead of "
        "using pip install --report.",
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
    # If install or freeze-args have been provided, split them into list
    if args.install_args:
        args.install_args = args.install_args.split(" ")
    if args.freeze_args:
        args.freeze_args = args.freeze_args.split(" ")
    return args


def main() -> None:
    arguments: argparse.Namespace = parse_args()
    if arguments.file.suffix == ".toml":
        dependencies: Optional[list[str]] = read_toml(
            arguments.file, arguments.dependency
        )
    else:
        dependencies = None
    if not arguments.venv:
        pip222_pin(
            python_exec=arguments.python,
            toml_dependencies=dependencies,
            requirements_in=arguments.file,
            output_file=arguments.output,
            install_args=arguments.install_args,
        )
    else:
        create_venv(arguments.python)
        install_packages(
            toml_dependencies=dependencies,
            requirements_in=arguments.file,
            install_args=arguments.install_args,
            verbose=arguments.verbose,
        )
        freeze_packages(
            output_file=arguments.output,
            input_file=arguments.file,
            freeze_args=arguments.freeze_args,
            verbose=arguments.verbose,
        )
        shutil.rmtree(TEMP_VENV)
    print(f"Pinned specified requirements in {arguments.output}")


if __name__ == "__main__":
    main()
