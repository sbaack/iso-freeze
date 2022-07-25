from typing import Final
from pathlib import Path

from iso_freeze import iso_freeze
from iso_freeze.iso_freeze import PyPackage

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
    mocked_pip_version_output_5 = "pip 34.2.9 from /funny/path/pip (python 3.15)"
    mocker.patch("subprocess.check_output", return_value=mocked_pip_version_output_5)
    assert iso_freeze.validate_pip_version(Path("python3")) == True


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


def test_build_pip_report_command(mocker):
    """Test whether pip command is build correctly."""
    # We don't want to make a subprocess call for this test
    mocker.patch("iso_freeze.iso_freeze.run_pip")
    # First test: requirements file
    pip_report_command_1 = iso_freeze.build_pip_report_command(
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
    pip_report_command_2 = iso_freeze.build_pip_report_command(
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
    pip_report_command_3 = iso_freeze.build_pip_report_command(
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
    pip_report_command_4 = iso_freeze.build_pip_report_command(
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


def test_remove_additional_packages(mocker):
    """Test if additional packages are properly detected and removed."""
    mocker.patch("iso_freeze.iso_freeze.run_pip")
    mocked_pip_list_output = [
        PyPackage(name="tomli", version="2.0.1", requested=False),
        # Two packages not in mocked pip report output
        PyPackage(name="pip", version="22.2", requested=False),
        PyPackage(name="cowsay", version="5.0", requested=False),
    ]
    mocked_pip_report_output = [
        PyPackage(name="tomli", version="2.0.1", requested=True),
        # One package not in mocked pip list output
        PyPackage(name="pyjokes", version="0.6.0", requested=True),
    ]
    iso_freeze.remove_additional_packages(
        installed_packages=mocked_pip_list_output,
        to_install=mocked_pip_report_output,
        python_exec=Path("python3"),
    )
    # pip should not be removed, cowsay should
    iso_freeze.run_pip.assert_called_with(
        command=[Path("python3"), "-m", "pip", "uninstall", "-y", "cowsay"],
        check_output=False,
    )


def test_get_installed_packages(mocker):
    """Test if pip list output correctly parsed."""
    mocked_pip_list_output = [
        {"name": "attrs", "version": "21.4.0"},
        {"name": "iniconfig", "version": "1.1.1"},
        {
            "name": "iso-freeze",
            "version": "0.0.10",
            "editable_project_location": "/Users/user/python_projects/iso-freeze",
        },
        {"name": "packaging", "version": "21.3"},
        {"name": "pip", "version": "22.2"},
        {"name": "pluggy", "version": "1.0.0"},
    ]
    expected_output = [
        PyPackage(name="attrs", version="21.4.0", requested=False),
        PyPackage(name="iniconfig", version="1.1.1", requested=False),
        PyPackage(name="iso-freeze", version="0.0.10", requested=False),
        PyPackage(name="packaging", version="21.3", requested=False),
        PyPackage(name="pip", version="22.2", requested=False),
        PyPackage(name="pluggy", version="1.0.0", requested=False),
    ]
    mocker.patch("json.loads", return_value=mocked_pip_list_output)
    actual_output = iso_freeze.get_installed_packages(python_exec=Path("python3"))
    assert actual_output == expected_output


def test_install_pip_report_output(mocker):
    """Test if pip report --install output is properly passed to pip install."""
    mocker.patch("iso_freeze.iso_freeze.run_pip")
    mocked_pip_report_output = [
        PyPackage(name="tomli", version="2.0.1", requested=True),
        PyPackage(name="pyjokes", version="0.6.0", requested=True),
    ]
    iso_freeze.install_pip_report_output(
        to_install=mocked_pip_report_output,
        python_exec=Path("python3"),
    )
    iso_freeze.run_pip.assert_called_with(
        command=[
            Path("python3"),
            "-m",
            "pip",
            "install",
            "--upgrade",
            "tomli==2.0.1",
            "pyjokes==0.6.0",
        ],
        check_output=False,
    )


def test_get_dependencies(mocker):
    """Test if pip install --report is correctly captured."""
    mocker.patch("iso_freeze.iso_freeze.run_pip")
    mocked_pip_report_output = {
        "environment": {},
        "install": [
            {
                "download_info": {
                    "archive_info": {"hash": "some_hash"},
                    "url": "some_url",
                },
                "is_direct": False,
                "metadata": {
                    "author_email": "Someone" "<someone@email.com>",
                    "classifier": ["License :: OSI Approved :: MIT "],
                    "description": "",
                    "keywords": ["something"],
                    "metadata_version": "2.1",
                    "name": "cool_package",
                    "project_url": [
                        "Homepage, " "https://github.com/",
                    ],
                    "requires_python": ">=3.7",
                    "summary": "A cool package",
                    "version": "2.0.1",
                },
                "requested": True,
            }
        ],
        "pip_version": "22.2",
        "version": "0",
    }
    expected_result = [PyPackage(name="cool_package", version="2.0.1", requested=True)]
    mocker.patch("json.loads", return_value=mocked_pip_report_output)
    mocked_pip_report_command = [
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
        "cowsay",
    ]
    actual_result = iso_freeze.get_dependencies(mocked_pip_report_command)
    assert actual_result == expected_result
