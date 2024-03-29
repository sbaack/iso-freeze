from typing import Any, Final, Optional, Union
from pathlib import Path

import pytest

from iso_freeze.lib import PyPackage
from iso_freeze.get_requirements import (
    read_toml,
    read_pip_report,
    build_pip_report_command,
)


TEST_TOML: Final[dict[str, Any]] = {
    "project": {
        "dependencies": ["tomli"],
        "optional-dependencies": {
            "dev": ["pytest", "pytest-mock"],
            "virtualenv": ["virtualenv"],
        },
    }
}

TEST_EMPTY_TOML: Final[dict[str, Any]] = {
    "something": {"no_project_section": "nothing"}
}

TEST_NO_OPS_TOML: Final[dict[str, Any]] = {
    "project": {
        "dependencies": ["tomli"],
    }
}


def test_read_toml_base_requirements() -> None:
    """Only return base requirements listed in TOML file."""
    base_requirements: list[str] = read_toml(
        toml_dict=TEST_TOML, optional_dependency=None
    )
    assert base_requirements == ["tomli"]


def test_read_toml_optional_dependency() -> None:
    """
    Return list that contains both base requirements and the specified optional
    dependency in TOML file.
    """
    dev_deps: list[str] = read_toml(toml_dict=TEST_TOML, optional_dependency="dev")
    assert dev_deps == [
        "tomli",
        "pytest",
        "pytest-mock",
    ]


def test_read_toml_missing_optional_dependency() -> None:
    """
    sys.exit() if user specifies an optional dependency that does exist in in TOML
    file.
    """
    with pytest.raises(SystemExit):
        read_toml(toml_dict=TEST_TOML, optional_dependency="something")


def test_read_toml_no_optional_dependencies() -> None:
    """
    sys.exit() if user specifies an optional dependency for TOML file that contains no
    optional dependencies at all.
    """
    with pytest.raises(SystemExit):
        read_toml(toml_dict=TEST_NO_OPS_TOML, optional_dependency="something")


def test_read_toml_no_project_section() -> None:
    """sys.exit() if TOML file contains no 'project' section."""
    with pytest.raises(SystemExit):
        read_toml(toml_dict=TEST_EMPTY_TOML, optional_dependency="something")


def test_build_pip_report_command() -> None:
    """Translate various inputs into corresponding pip report commands."""
    # First test: requirements file
    pip_report_command_1: list[Union[str, Path]] = build_pip_report_command(
        pip_report_input=["-r", Path("requirements.in")],
        python_exec=Path("python3"),
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
    pip_report_command_2: list[Union[str, Path]] = build_pip_report_command(
        pip_report_input=["tomli", "pytest", "pytest-mock"],
        python_exec=Path("python3"),
        pip_args=None,
    )
    expected_pip_report_command_2: list[Union[str, Path]] = [
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
    pip_report_command_3: list[Union[str, Path]] = build_pip_report_command(
        pip_report_input=["tomli", "pytest", "pytest-mock"],
        python_exec=Path("python3"),
        pip_args=["--upgrade-strategy", "eager", "--retries", "10"],
    )
    expected_pip_report_command_3: list[Union[str, Path]] = [
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
    pip_report_command_4: list[Union[str, Path]] = build_pip_report_command(
        pip_report_input=["-r", Path("requirements.in")],
        python_exec=Path("python3"),
        pip_args=["--upgrade-strategy", "eager", "--require-hashes"],
    )
    expected_pip_report_command_4: list[Union[str, Path]] = [
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


def test_read_pip_report() -> None:
    """
    Pip report output is turned into list of PyPackage objects capturing names, versions
    and hashes of packages, or None if pip report's 'install' section is empty.
    """
    mocked_pip_report_output: dict[str, Any] = {
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
    expected_result_1: Optional[list[PyPackage]] = [
        PyPackage(
            name="cool_package",
            version="2.0.1",
            requested=True,
            hash="sha256:some_hash",
        )
    ]
    actual_result_1: Optional[list[PyPackage]] = read_pip_report(
        mocked_pip_report_output
    )
    assert actual_result_1 == expected_result_1
    mocked_pip_report_output_no_install: dict[str, Any] = {
        "environment": {},
        "install": [],
        "pip_version": "22.2",
        "version": "0",
    }
    expected_result_2: Optional[list[PyPackage]] = None
    actual_result_2: Optional[list[PyPackage]] = read_pip_report(
        mocked_pip_report_output_no_install
    )
    assert actual_result_2 == expected_result_2
