"""Write *requirements.txt file."""

from pathlib import Path

from iso_freeze.lib import PyPackage


def pin_requirements(
    requirements: list[PyPackage], hashes: bool, output_file: Path
) -> None:
    """Write *requirements.txt file.

    Arguments:
        requirements -- List of packages to pin (list[PyPackage])
        hashes -- Whether to include hashes (bool)
        output_file -- Path to file that should be created (Path)
    """
    output_file_contents: list[str] = build_reqirements_file_contents(
        requirements=requirements, hashes=hashes
    )
    write_requirements_file(output_file=output_file, file_contents=output_file_contents)
    print(f"Pinned specified requirements in {output_file}")


def build_reqirements_file_contents(
    requirements: list[PyPackage], hashes: bool
) -> list[str]:
    """Build contents of requirements file as a list.

    Display top level dependencies on top, similar to pip freeze -r requirements_file.

    Arguments:
        requirements -- Dependencies listed in pip install --report (list[dict[str]])
        hashes -- Whether to include hashes (bool)

    Returns:
        Contents of requirements file (list[str])
    """
    # For easier formatting we create separate lists for top level requirements
    # and their dependencies
    top_level_requirements: list[str] = []
    dependency_requirements: list[str] = []
    for package in requirements:
        pinned_format: str = f"{package.name}=={package.version}"
        if hashes:
            pinned_format += f" \\\n    --hash={package.hash}"
        # If requested == True, the package is a top level requirement
        if package.requested:
            top_level_requirements.append(pinned_format)
        else:
            dependency_requirements.append(pinned_format)
    # Sort pinned packages alphabetically before writing to file
    # (case-insensitively thanks to key=str.lower)
    top_level_requirements.sort(key=str.lower)
    # Combine lists and add comments
    requirements_file_content: list[str] = [
        "# Top level requirements",
        *top_level_requirements,
    ]
    if dependency_requirements:
        dependency_requirements.sort(key=str.lower)
        requirements_file_content.extend(
            ["# Dependencies of top level requirements", *dependency_requirements]
        )
    return requirements_file_content


def write_requirements_file(output_file: Path, file_contents: list[str]) -> None:
    """Write requirements file.

    Arguments:
        output_file -- Path to and name of requirements.txt file (Path)
        file_contents -- Contents to to written to a file (list[str])
    """
    with output_file.open(mode="w", encoding="utf=8") as f:
        f.writelines(f"{package}\n" for package in file_contents)
