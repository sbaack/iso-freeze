import os
import sys

from pathlib import Path
import pytest

from iso_freeze.cli import determine_default_file, validate_pip_version, parse_args


def test_determine_default() -> None:
    """
    requirements.in or pyproject.toml picked as default file if found in working
    directory, or None if neither is present.
    """
    # If only requirements.in found, return that
    os.chdir(Path(Path(__file__).parent.resolve(), "test_directories", "requirements"))
    assert determine_default_file() == Path("requirements.in")
    # If only pyproject.toml found, return that
    os.chdir(Path(Path(__file__).parent.resolve(), "test_directories", "pyproject"))
    assert determine_default_file() == Path("pyproject.toml")
    # If neither requirements.in or pyproject.toml, return None
    os.chdir(Path(Path(__file__).parent.resolve(), "test_directories", "neither"))
    assert determine_default_file() is None
    # If both requirements.in or pyproject.toml, return requirements.in
    os.chdir(Path(Path(__file__).parent.resolve(), "test_directories", "both"))
    assert determine_default_file() == Path("requirements.in")


def test_validate_pip_version() -> None:
    """
    Validate pip version number from pip --version output, True if >= 22.2, else False.
    """
    mocked_pip_version_output_1 = "pip 22.2 from /funny/path/pip (python 3.9)"
    assert validate_pip_version(pip_version_output=mocked_pip_version_output_1) is True
    mocked_pip_version_output_2 = "pip 22.1 from /funny/path/pip (python 3.9)"
    assert validate_pip_version(pip_version_output=mocked_pip_version_output_2) is False
    mocked_pip_version_output_3 = "pip 23.1 from /funny/path/pip (python 3.10)"
    assert validate_pip_version(pip_version_output=mocked_pip_version_output_3) is True
    mocked_pip_version_output_4 = "pip 20.1.3 from /funny/path/pip (python 3.8)"
    assert validate_pip_version(pip_version_output=mocked_pip_version_output_4) is False
    mocked_pip_version_output_5 = "pip 34.2.9 from /funny/path/pip (python 3.15)"
    assert validate_pip_version(pip_version_output=mocked_pip_version_output_5) is True


def test_parse_args() -> None:
    """Test of args are correctly parsed."""
    sys.argv[1:] = ["pyproject.toml", "-d", "dev"]
    test_args1 = parse_args()
    assert test_args1.python == Path("python3")
    assert test_args1.dependency == "dev"
    assert test_args1.file == Path("pyproject.toml")
    assert test_args1.output == Path("requirements.txt")
    sys.argv[1:] = ["requirements.in", "--pip-args", "--upgrade-strategy eager"]
    test_args2 = parse_args()
    assert test_args2.pip_args == ["--upgrade-strategy", "eager"]
    assert test_args2.sync is False
    assert test_args2.hashes is False


def test_input_file_doesnt_exist() -> None:
    """sys.exit() if specified file doesn't exist."""
    sys.argv[1:] = ["some file that should not exist!!!111"]
    with pytest.raises(SystemExit) as e:
        parse_args()
    assert e.type == SystemExit


def test_no_default_file_found() -> None:
    """
    sys.exit() if no file specified and neither requirements.in or pyproject.toml in
    working directory.
    """
    os.chdir(Path(Path(__file__).parent.resolve(), "test_directories", "neither"))
    with pytest.raises(SystemExit) as e:
        parse_args()
    assert e.type == SystemExit


def test_combine_requirements_dependency() -> None:
    """sys.exit() when optional dependency specified for requirements file."""
    sys.argv[1:] = ["requirements.in", "-d", "dev"]
    with pytest.raises(SystemExit) as e:
        parse_args()
    assert e.type == SystemExit
