from iso_freeze.lib import PyPackage
from iso_freeze.pin_requirements import build_reqirements_file_contents

MOCKED_REQUIREMENTS = [
    PyPackage(name="tomli", version="2.0.1", requested=True, hash="sha256:1234"),
    PyPackage(name="pyjokes", version="0.6.0", requested=False, hash="sha256:5678"),
]


def test_build_reqirements_file_contents_no_hashes() -> None:
    """
    List used to build requirement files adds distinction between top level
    requirements and their dependencies via comments.
    """
    expected_output_no_hashes: list[str] = [
        "# Top level requirements",
        "tomli==2.0.1",
        "# Dependencies of top level requirements",
        "pyjokes==0.6.0",
    ]
    actual_output_no_hashes: list[str] = build_reqirements_file_contents(
        requirements=MOCKED_REQUIREMENTS, hashes=False
    )
    assert expected_output_no_hashes == actual_output_no_hashes


def test_build_reqirements_file_contents_with_hashes() -> None:
    """
    List used to build requirement files adds distinction between top level
    requirements and their dependencies via comments, and hashes are added
    correctly.
    """
    expected_output_hashes = [
        "# Top level requirements",
        "tomli==2.0.1 \\\n" "    --hash=sha256:1234",
        "# Dependencies of top level requirements",
        "pyjokes==0.6.0 \\\n" "    --hash=sha256:5678",
    ]
    actual_output_hashes: list[str] = build_reqirements_file_contents(
        requirements=MOCKED_REQUIREMENTS, hashes=True
    )
    assert expected_output_hashes == actual_output_hashes
