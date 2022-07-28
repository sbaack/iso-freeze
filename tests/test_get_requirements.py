import sys
from typing import Final
from pathlib import Path

from iso_freeze.get_requirements import *


TEST_TOML: Final[Path] = Path(Path(__file__).parent.resolve(), "test_pyproject.toml")


def test_read_toml():
    """Test whether correct list of requirements is returned."""
    dev_deps = read_toml(toml_file=TEST_TOML, optional_dependency="dev")
    assert dev_deps == ["tomli", "pytest", "pytest-mock"]

    virtualenv_deps = read_toml(toml_file=TEST_TOML, optional_dependency="virtualenv")
    assert virtualenv_deps == ["tomli", "virtualenv"]

    base_requirements = read_toml(toml_file=TEST_TOML, optional_dependency=None)
    assert base_requirements == ["tomli"]


def test_build_pip_report_command():
    """Test whether pip command is build correctly."""
    # First test: requirements file
    pip_report_command_1 = build_pip_report_command(
        file=Path("requirements.in"),
        python_exec=Path("python3"),
        pip_args=None,
        optional_dependency=None
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
    pip_report_command_2 = build_pip_report_command(
        file=TEST_TOML,
        python_exec=Path("python3"),
        pip_args=None,
        optional_dependency="dev"
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
        "tomli",
        "pytest",
        "pytest-mock",
    ]
    assert pip_report_command_2 == expected_pip_report_command_2
    # Third test: TOML dependencies with pip-args
    pip_report_command_3 = build_pip_report_command(
        file=TEST_TOML,
        python_exec=Path("python3"),
        pip_args=["--upgrade-strategy", "eager", "--retries", "10"],
        optional_dependency="dev"
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
        "--retries",
        "10",
        "-q",
        "--dry-run",
        "--ignore-installed",
        "--report",
        "-",
        "tomli",
        "pytest",
        "pytest-mock",
    ]
    assert pip_report_command_3 == expected_pip_report_command_3
    # Fourth test: requirements file with pip-args
    pip_report_command_4 = build_pip_report_command(
        file=Path("requirements.in"),
        python_exec=Path("python3"),
        pip_args=["--upgrade-strategy", "eager", "--require-hashes"],
        optional_dependency=None,
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


def test_read_pip_report():
    """Test if pip install --report is correctly captured."""
    mocked_pip_report_output = {
        "environment": {},
        "install": [
            {
                "download_info": {
                    "archive_info": {"hash": "sha256=some_hash"},
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
    expected_result = [
        PyPackage(
            name="cool_package",
            version="2.0.1",
            requested=True,
            hash="sha256:some_hash",
        )
    ]
    actual_result = read_pip_report(mocked_pip_report_output)
    assert actual_result == expected_result
    mocked_pip_report_output_no_install = {
        "environment": {},
        "install": [],
        "pip_version": "22.2",
        "version": "0",
    }
    expected_result = None
    actual_result = read_pip_report(mocked_pip_report_output_no_install)
    assert actual_result == expected_result
