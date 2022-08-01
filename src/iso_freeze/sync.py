"""Sync environment with pip install --report output."""

import json
from pathlib import Path
from typing import Optional

from iso_freeze.lib import PyPackage, run_pip


def sync(requirements: list[PyPackage], python_exec: Path) -> None:
    """Sync environment with pip install --report output.

    Arguments:
        requirements -- List of dependencies to sync with (list[PyPackage])
        python_exec -- Path to Python interpreter to use (Path)
    """
    installed_packages: list[PyPackage] = get_installed_packages(
        pip_list_output=get_pip_list_output(python_exec=python_exec)
    )
    additional_packages: Optional[list[str]] = get_additional_packages(
        installed_packages=installed_packages,
        to_install=requirements,
    )
    if additional_packages:
        remove_additional_packages(
            additional_packages=additional_packages,
            python_exec=python_exec,
        )
    install_pip_report_output(
        to_install=format_package_list(packages=requirements),
        python_exec=python_exec,
    )


def get_pip_list_output(python_exec: Path) -> list[dict[str, str]]:
    """Run pip list --format json output.

    Arguments:
        python_exec -- Path to Python interpreter to use (Path)

    Returns:
        Pip list output as JSON (list[dict[str, str]])
    """
    return json.loads(
        run_pip(
            command=[
                python_exec,
                "-m",
                "pip",
                "list",
                "--format",
                "json",
                "--exclude-editable",
            ],
            check_output=True,
        )
    )


def get_installed_packages(pip_list_output: list[dict[str, str]]) -> list[PyPackage]:
    """Return pip list output as PyPackage objects.

    Arguments:
        pip_list_output -- Pip list output as JSON (list[dict[str, str]])

    Returns:
        List of packages from current environment (list[PyPackage])
    """
    return [
        PyPackage(name=package["name"], version=package["version"])
        for package in pip_list_output
    ]


def get_additional_packages(
    installed_packages: list[PyPackage], to_install: list[PyPackage]
) -> Optional[list[str]]:
    """Filter out pip packages installed in current environment but not in pip report.

    Arguments:
        installed_packages -- List of packages installed in current environment
                              (list[PyPackage])
        to_install -- List of packages taken from pip install --report
                      (list[PyPackages])

    Returns:
        List of installed packages not in pip report (Optional[list[str]])
    """
    # Create two lists with packages names only for easy comparison
    installed_names_only: list[str] = [package.name for package in installed_packages]
    to_install_names_only: list[str] = [package.name for package in to_install]
    return [
        package
        for package in installed_names_only
        if package not in to_install_names_only
        # Don't remove default packages
        if package not in ["pip", "setuptools"]
    ]


def remove_additional_packages(
    additional_packages: Optional[list[str]], python_exec: Path
) -> None:
    """Remove installed packages not included in pip install --report.

    Arguments:
        additional_packages -- List of packages to remove (Optional[list[str]])
        python_exec -- Path to Python executable (Path)
    """
    run_pip(
        command=[python_exec, "-m", "pip", "uninstall", "-y", *additional_packages],
        check_output=False,
    )


def format_package_list(packages: list[PyPackage]) -> list[str]:
    """Create list in the format ["package1==versionX"] to pass that to `pip install`.

    Arguments:
        packages -- List of packages to install (list[PyPackage])

    Returns:
        List of packages to be passed to pip install (list[str])
    """
    return [f"{package.name}=={package.version}" for package in packages]


def install_pip_report_output(to_install: list[str], python_exec: Path) -> None:
    """Install packages with pinned versions from pip install --report output.

    Arguments:
        to_install -- List of packages taken from pip install --report (list[str])
        python_exec -- Path to Python executable (Path)
    """
    run_pip(
        command=[python_exec, "-m", "pip", "install", "--upgrade", *to_install],
        check_output=False,
    )
