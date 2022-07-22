from typing import Final
from pathlib import Path

from iso_freeze import iso_freeze


TEST_TOML: Final[Path] = Path(Path(__file__).parent.resolve(), "test_pyproject.toml")


def test_validate_pip_version(mocker):
    """Test whether pip version is validated correctly."""
    mocked_pip_version_output_1 = "pip 22.2 from /funny/path/pip (python 3.9)"
    mocker.patch("subprocess.check_output", return_value=mocked_pip_version_output_1)
    assert iso_freeze.validate_pip_version(Path("python3")) == True
    mocked_pip_version_output_2 = "pip 22.1 from /funny/path/pip (python 3.9)"
    mocker.patch("subprocess.check_output", return_value=mocked_pip_version_output_2)
    assert iso_freeze.validate_pip_version(Path("python3")) == False
    mocked_pip_version_output_3 = "pip 23.1 from /funny/path/pip (python 3.10)"
    mocker.patch("subprocess.check_output", return_value=mocked_pip_version_output_3)
    assert iso_freeze.validate_pip_version(Path("python3")) == True
    mocked_pip_version_output_4 = "pip 20.1.3 from /funny/path/pip (python 3.8)"
    mocker.patch("subprocess.check_output", return_value=mocked_pip_version_output_4)
    assert iso_freeze.validate_pip_version(Path("python3")) == False


def test_dev_deps():
    """Test whether the correct list of requirements with optional dependency is loaded."""
    dev_deps = iso_freeze.read_toml(toml_file=TEST_TOML, optional_dependency="dev")
    assert dev_deps == ["tomli", "pytest", "pytest-mock"]


def test_virtualenv_deps():
    """Test whether the correct list of requirements with optional dependency is loaded.
    
    Using a different optional dependency.
    """
    virtualenv_deps = iso_freeze.read_toml(
        toml_file=TEST_TOML, optional_dependency="virtualenv"
    )
    assert virtualenv_deps == ["tomli", "virtualenv"]


def test_base_requirements():
    """Test whether the correct list of base requirements is loaded."""
    base_requirements = iso_freeze.read_toml(
        toml_file=TEST_TOML, optional_dependency=None
    )
    assert base_requirements == ["tomli"]


def test_build_pip_command(mocker):
    """Test whether pip command is build correctly."""
    # We don't want to make a subprocess call for this test
    mocker.patch("iso_freeze.iso_freeze.run_pip_report")
    # First test: requirements file
    pip_report_command_1 = iso_freeze.build_pip_command(
        python_exec=Path("python3"),
        toml_dependencies=None,
        requirements_in=Path("requirements.in"),
        pip_args=None,
    )
    expected_pip_report_command_1 = [
        "env",
        "PIP_REQUIRE_VIRTUALENV=false",
        Path("python3"),
        "-m",
        "pip",
        "install",
        "-q",
        "--dry-run",
        "--ignore-installed",
        "--report",
        "-",
        "-r",
        Path("requirements.in"),
    ]
    assert pip_report_command_1 == expected_pip_report_command_1
    # Second test: TOML dependencies
    pip_report_command_2 = iso_freeze.build_pip_command(
        python_exec=Path("python3"),
        toml_dependencies=["pytest", "pytest-mock"],
        requirements_in=None,
        pip_args=None,
    )
    expected_pip_report_command_2 = [
        "env",
        "PIP_REQUIRE_VIRTUALENV=false",
        Path("python3"),
        "-m",
        "pip",
        "install",
        "-q",
        "--dry-run",
        "--ignore-installed",
        "--report",
        "-",
        "pytest",
        "pytest-mock",
    ]
    assert pip_report_command_2 == expected_pip_report_command_2
    # Third test: TOML dependencies with pip-args
    pip_report_command_3 = iso_freeze.build_pip_command(
        python_exec=Path("python3"),
        toml_dependencies=["pytest", "pytest-mock"],
        requirements_in=None,
        pip_args=["--upgrade-strategy", "eager", "--require-hashes"],
    )
    expected_pip_report_command_3 = [
        "env",
        "PIP_REQUIRE_VIRTUALENV=false",
        Path("python3"),
        "-m",
        "pip",
        "install",
        "--upgrade-strategy",
        "eager",
        "--require-hashes",
        "-q",
        "--dry-run",
        "--ignore-installed",
        "--report",
        "-",
        "pytest",
        "pytest-mock",
    ]
    assert pip_report_command_3 == expected_pip_report_command_3
    # Fourth test: requirements file with pip-args
    pip_report_command_4 = iso_freeze.build_pip_command(
        python_exec=Path("python3"),
        toml_dependencies=None,
        requirements_in=Path("requirements.in"),
        pip_args=["--upgrade-strategy", "eager", "--require-hashes"],
    )
    expected_pip_report_command_4 = [
        "env",
        "PIP_REQUIRE_VIRTUALENV=false",
        Path("python3"),
        "-m",
        "pip",
        "install",
        "--upgrade-strategy",
        "eager",
        "--require-hashes",
        "-q",
        "--dry-run",
        "--ignore-installed",
        "--report",
        "-",
        "-r",
        Path("requirements.in"),
    ]
    assert pip_report_command_4 == expected_pip_report_command_4
