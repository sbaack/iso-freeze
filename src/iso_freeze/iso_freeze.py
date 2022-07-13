"""Call pip freeze in isolated venv to cleanly separate pinned requirements for
different optional dependencies (e.g. 'dev' and 'doc' requirements)."""

import argparse
import subprocess
import shutil
import sys
from typing import Optional, Final
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
    dependencies: list[str] = metadata["project"].get("dependencies")
    if optional_dependency:
        optional_dependency_reqs: Optional[list[str]] = (
            metadata["project"].get("optional-dependencies").get(optional_dependency)
        )
        if optional_dependency_reqs:
            dependencies.extend(optional_dependency_reqs)
        else:
            sys.exit(
                f"No optional dependency named {optional_dependency} found in your "
                "pyproject.toml"
            )
    return dependencies


def install_packages(
    dependencies: Optional[list[str]],
    requirements_in: Optional[Path],
    pip_args: Optional[list[str]],
) -> None:
    """Install packages listed in pyproject.toml or in a requirements file into
    temporary venv.

    Arguments:
        dependencies -- names of dependencies to install (Optional[list[str]])
        requirements_in -- path to requirements file (Optional[Path])
        pip_args -- arguments to be passed to pip (Optional[list[str]])
    """
    pip_install_command = [
        TEMP_VENV_EXEC,
        "-m",
        "pip",
        "install",
        *pip_args,
        "-q",
        "-U",
    ]
    if dependencies:
        pip_install_command.extend([dependency for dependency in dependencies])
    elif requirements_in:
        pip_install_command.extend(["-r", requirements_in])
    run_pip_install(pip_install_command=pip_install_command)


def run_pip_install(pip_install_command: list[str]) -> None:
    """Run pip install."""
    try:
        subprocess.run(pip_install_command, check=True)
    except subprocess.CalledProcessError as error:
        shutil.rmtree(TEMP_VENV)
        error.output
        sys.exit()


def create_venv() -> None:
    """Create temporary venv."""
    try:
        subprocess.run(["python3", "-m", "venv", TEMP_VENV.name], check=True)
        subprocess.run(
            [TEMP_VENV_EXEC, "-m", "pip", "install", "-q", "-U", "pip"], check=True
        )
    except subprocess.CalledProcessError as error:
        shutil.rmtree(TEMP_VENV)
        error.output
        sys.exit()


def run_pip_freeze(output_file: Path) -> None:
    """Create pinned requirements file.

    Arguments:
        output_file -- Path and name of output file
    """
    pip_freeze_output: bytes = subprocess.check_output(
        [TEMP_VENV_EXEC, "-m", "pip", "-q", "freeze"]
    )
    if pip_freeze_output:
        output_file.write_text(pip_freeze_output.decode("utf-8"))
    else:
        shutil.rmtree(TEMP_VENV)
        sys.exit("There are no dependencies to pin")


def determine_default_file() -> Path:
    """Determine default input file if none has been specified.

    Returns:
        Path to default file [Path]
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
        description="Call pip freeze in isolated venv to cleanly separate pinned "
        "requirements for different optional dependencies (e.g. 'dev' and 'doc' "
        "requirements)."
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
        "--pip-args",
        # Set default to empty list to enable unpacking in install function even if
        # pip-args haven't been set
        default=[],
        help="List of arguments to be passed to pip install. Call as: "
             "pip-args \"--pip-arg1 value --pip-arg2 value\"",
    )
    args = argparser.parse_args()
    if not args.file:
        sys.exit(
            "No requirements.in or pyproject.toml file found in current directory. "
            "Please specify input file."
        )
    if args.file.name != "pyproject.toml" and args.dependency:
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
    arguments: argparse.Namespace = parse_args()
    create_venv()
    if arguments.file.name == "pyproject.toml":
        dependencies: Optional[list[str]] = read_toml(
            arguments.file, arguments.dependency
        )
    else:
        dependencies = None
    install_packages(
        dependencies=dependencies,
        requirements_in=arguments.file,
        pip_args=arguments.pip_args,
    )
    run_pip_freeze(arguments.output)
    shutil.rmtree(TEMP_VENV)
    print(f"Pinned specified requirements in {arguments.output}")


if __name__ == "__main__":
    main()
