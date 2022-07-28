import os

from pathlib import Path

from iso_freeze.cli import *


def test_determine_default():
    """Test whether correct default file is picked if none is specified."""
    # If only requirements.in found, return that
    os.chdir(Path(Path(__file__).parent.resolve(), "test_directories", "requirements"))
    assert determine_default_file() == Path("requirements.in")
    # If only pyproject.toml found, return that
    os.chdir(Path(Path(__file__).parent.resolve(), "test_directories", "pyproject"))
    assert determine_default_file() == Path("pyproject.toml")
    # If neither requirements.in or pyproject.toml, return None
    os.chdir(Path(Path(__file__).parent.resolve(), "test_directories", "neither"))
    assert determine_default_file() == None
    # If both requirements.in or pyproject.toml, return requirements.in
    os.chdir(Path(Path(__file__).parent.resolve(), "test_directories", "both"))
    assert determine_default_file() == Path("requirements.in")


def test_validate_pip_version():
    """Test whether pip version is validated correctly."""
    mocked_pip_version_output_1 = "pip 22.2 from /funny/path/pip (python 3.9)"
    assert validate_pip_version(pip_version_output=mocked_pip_version_output_1) == True
    mocked_pip_version_output_2 = "pip 22.1 from /funny/path/pip (python 3.9)"
    assert validate_pip_version(pip_version_output=mocked_pip_version_output_2) == False
    mocked_pip_version_output_3 = "pip 23.1 from /funny/path/pip (python 3.10)"
    assert validate_pip_version(pip_version_output=mocked_pip_version_output_3) == True
    mocked_pip_version_output_4 = "pip 20.1.3 from /funny/path/pip (python 3.8)"
    assert validate_pip_version(pip_version_output=mocked_pip_version_output_4) == False
    mocked_pip_version_output_5 = "pip 34.2.9 from /funny/path/pip (python 3.15)"
    assert validate_pip_version(pip_version_output=mocked_pip_version_output_5) == True


def test_parse_args():
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
    assert test_args2.sync == False
    assert test_args2.hashes == False
