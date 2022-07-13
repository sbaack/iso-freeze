import sys
from pathlib import Path

if sys.version_info >= (3, 11, 0):
    import tomllib
else:
    import tomli as tomllib  # type: ignore

from iso_freeze import iso_freeze


def test_temp_venv_exec_path():
    """Test whether TEMP_VENV_EXEC is correctly constructed on different OS."""
    if sys.platform == "win32":
        assert iso_freeze.TEMP_VENV_EXEC == Path(
            iso_freeze.TEMP_VENV, "Scripts", "python"
        )
    else:
        assert iso_freeze.TEMP_VENV_EXEC == Path(iso_freeze.TEMP_VENV, "bin", "python")


def load_test_toml():
    """Return a test TOML string."""
    test_toml = """
    [project]
    dependencies = [
        "tomli"
    ]

    [project.optional-dependencies]
    dev = [
        "pytest",
        "pytest-mock"
    ]
    virtualenv = [
        "virtualenv"
    ]
    """
    return tomllib.loads(test_toml)

def test_dev_deps(mocker):
    """Test whether the correct list of requirements is loaded."""
    data = load_test_toml()
    mocker.patch("tomllib.load", return_value=data)
    dev_deps = iso_freeze.read_toml(toml_file=Path(__file__).resolve(), optional_dependency="dev")
    assert dev_deps == ["tomli", "pytest", "pytest-mock"]

def test_virtualenv_deps(mocker):
    """Test whether the correct list of requirements is loaded."""
    data = load_test_toml()
    mocker.patch("tomllib.load", return_value=data)
    virtualenv_deps = iso_freeze.read_toml(toml_file=Path(__file__).resolve(), optional_dependency="virtualenv")
    assert virtualenv_deps == ["tomli", "virtualenv"]

def test_base_requirements(mocker):
    """Test whether the correct list of requirements is loaded."""
    data = load_test_toml()
    mocker.patch("tomllib.load", return_value=data)
    base_requirements = iso_freeze.read_toml(toml_file=Path(__file__).resolve(), optional_dependency=None)
    assert base_requirements == ["tomli"]


def test_install_package(mocker):
    """Test whether pip install command is correct."""
    mocker.patch("iso_freeze.iso_freeze.run_pip_install")
    iso_freeze.install_packages(
        dependencies=["pytest", "pytest-mock"],
        requirements_in=None,
        pip_args=[],
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
        pip_args=["--upgrade-strategy", "eager"],
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


def test_create_venv(mocker):
    """Test if venv is created with correct command."""
    mocker.patch("iso_freeze.iso_freeze.run_venv_creation")
    virtualenv_command = [
        "python3",
        "-m",
        "virtualenv",
        "--no-setuptools",
        "--no-wheel",
        "-q",
        iso_freeze.TEMP_VENV.name,
    ]
    venv_command = ["python3", "-m", "venv", iso_freeze.TEMP_VENV.name]
    mocker.patch("importlib.util.find_spec", return_value=True)
    iso_freeze.create_venv()
    iso_freeze.run_venv_creation.assert_called_with == virtualenv_command
    mocker.patch("importlib.util.find_spec", return_value=False)
    iso_freeze.create_venv()
    iso_freeze.run_venv_creation.assert_called_with == venv_command