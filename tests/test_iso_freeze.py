import sys
from pathlib import Path

from iso_freeze import iso_freeze


TEST_TOML: Path = Path(Path(__file__).parent.resolve(), "test_pyproject.toml")


def test_temp_venv_exec_path():
    """Test whether TEMP_VENV_EXEC is correctly constructed on different OS."""
    if sys.platform == "win32":
        assert iso_freeze.TEMP_VENV_EXEC == Path(
            iso_freeze.TEMP_VENV, "Scripts", "python"
        )
    else:
        assert iso_freeze.TEMP_VENV_EXEC == Path(iso_freeze.TEMP_VENV, "bin", "python")


def test_dev_deps():
    """Test whether the correct list of requirements is loaded."""
    dev_deps = iso_freeze.read_toml(TEST_TOML, optional_dependency="dev")
    assert dev_deps == ["tomli", "pytest", "pytest-mock"]


def test_virtualenv_deps():
    """Test whether the correct list of requirements is loaded."""
    virtualenv_deps = iso_freeze.read_toml(TEST_TOML, optional_dependency="virtualenv")
    assert virtualenv_deps == ["tomli", "virtualenv"]


def test_base_requirements():
    """Test whether the correct list of requirements is loaded."""
    base_requirements = iso_freeze.read_toml(TEST_TOML, optional_dependency=None)
    assert base_requirements == ["tomli"]


def test_install_package(mocker):
    """Test whether pip install command is correct."""
    mocker.patch("iso_freeze.iso_freeze.run_pip_install")
    iso_freeze.install_packages(
        dependencies=["pytest", "pytest-mock"],
        requirements_in=None,
        install_args=[],
    )
    mocked_pip_install_command_1 = [
        iso_freeze.TEMP_VENV_EXEC,
        "-m",
        "pip",
        "install",
        "-q",
        "-U",
        "pytest",
        "pytest-mock",
    ]
    iso_freeze.run_pip_install.assert_called_with == mocked_pip_install_command_1
    iso_freeze.install_packages(
        dependencies=None,
        requirements_in=Path("requirements.in"),
        install_args=["--upgrade-strategy", "eager"],
    )
    mocked_pip_install_command_2 = [
        iso_freeze.TEMP_VENV_EXEC,
        "-m",
        "pip",
        "install",
        "--upgrade-strategy",
        "eager" "-q",
        "-U",
        "-r",
        "requirements.in",
    ]
    iso_freeze.run_pip_install.assert_called_with == mocked_pip_install_command_2


def test_freeze_packages(mocker):
    """Test whether pip freeze command is correct."""
    mocker.patch("iso_freeze.iso_freeze.run_pip_freeze")
    mocked_pip_freeze_command_1 = [
        iso_freeze.TEMP_VENV_EXEC,
        "-m",
        "pip",
        "-q",
        "freeze",
        "-r",
        "requirements.in",
    ]
    iso_freeze.freeze_packages(
        output_file=Path("requirements.txt"),
        input_file=Path("requirements.in"),
        freeze_args=None,
    )
    iso_freeze.run_pip_freeze.assert_called_with = mocked_pip_freeze_command_1
    mocked_pip_freeze_command_2 = [
        iso_freeze.TEMP_VENV_EXEC,
        "-m",
        "pip",
        "-q",
        "freeze",
        "--local",
        "--all",
        "-r",
        "requirements.in",
    ]
    iso_freeze.freeze_packages(
        output_file=Path("requirements.txt"),
        input_file=Path("requirements.in"),
        freeze_args=["--local", "--all"],
    )
    iso_freeze.run_pip_freeze.assert_called_with = mocked_pip_freeze_command_2
    mocked_pip_freeze_command_3 = [
        iso_freeze.TEMP_VENV_EXEC,
        "-m",
        "pip",
        "-q",
        "freeze",
        "--local",
        "--exclude",
        "tomli",
    ]
    iso_freeze.freeze_packages(
        output_file=Path("requirements.txt"),
        input_file=Path("requirements.in"),
        freeze_args=["--local", "--exclude", "tomli"],
    )
    iso_freeze.run_pip_freeze.assert_called_with = mocked_pip_freeze_command_3
