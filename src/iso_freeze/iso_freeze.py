"""Call pip freeze in isolated venv to cleanly separate pinned requirements for
different optional dependencies (e.g. 'dev' and 'doc' requirements)."""

import argparse
import subprocess
import shutil
import importlib.util
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


def install_toml(dependencies: list[str]) -> None:
    """Install dependencies listed in pyproject.toml in temporary venv.

    Arguments:
        dependencies -- names of dependencies to install (list[str])
    """
    try:
        subprocess.run(
            [TEMP_VENV_EXEC, "-m", "pip", "install", "-q", "-U", *dependencies],
            check=True,
        )
    except subprocess.CalledProcessError as error:
        shutil.rmtree(TEMP_VENV)
        error.output
        sys.exit()


def install_requirements_in(requirements_in: Path) -> None:
    """Install dependencies listed in requirements file to temporary venv.

    Keyword Arguments:
        requirements_in -- Path to requirements file
    """
    try:
        subprocess.run(
            [TEMP_VENV_EXEC, "-m", "pip", "install", "-q", "-Ur", requirements_in],
            check=True,
        )
    except subprocess.CalledProcessError as error:
        shutil.rmtree(TEMP_VENV)
        error.output
        sys.exit()


def create_venv() -> None:
    """Create temporary venv.

    Uses virtualenv if available, otherwise falls back to Python venv.
    """
    virtualenv_installed = importlib.util.find_spec("virtualenv")
    if virtualenv_installed:
        create_venv_command: list[str] = [
            sys.executable,
            "-m",
            "virtualenv",
            "--no-setuptools",
            "--no-wheel",
            "-q",
            TEMP_VENV.name,
        ]
    else:
        create_venv_command = [sys.executable, "-m", "venv", TEMP_VENV.name]
    subprocess.run(create_venv_command)
    subprocess.run([TEMP_VENV_EXEC, "-m", "pip", "install", "-q", "-U", "pip"])


def freeze_venv(output_file: Path) -> None:
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


def determine_default() -> Path:
    """Determine default input file if none has been specified.

    Returns:
        Path to default file [Path]
    """
    if Path("requirements.in").exists():
        default: Path = Path("requirements.in")
    elif Path("pyproject.toml").exists():
        default = Path("pyproject.toml")
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
        default=determine_default(),
        help="Path to input file. Can be pyproject.toml or requirements files. "
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
    return args


def main() -> None:
    arguments: argparse.Namespace = parse_args()
    create_venv()
    if arguments.file.name == "pyproject.toml":
        install_toml(read_toml(arguments.file, arguments.dependency))
    else:
        install_requirements_in(arguments.file)
    freeze_venv(arguments.output)
    shutil.rmtree(TEMP_VENV)
    print(f"Pinned specified requirements in {arguments.output}")


if __name__ == "__main__":
    main()
