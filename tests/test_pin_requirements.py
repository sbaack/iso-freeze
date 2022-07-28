from iso_freeze.pin_requirements import *


def test_build_reqirements_file_contents():
    """Test if requirements file contents are correctly build."""
    mocked_requirements = [
        PyPackage(name="tomli", version="2.0.1", requested=True, hash="sha256:1234"),
        PyPackage(name="pyjokes", version="0.6.0", requested=False, hash="sha256:5678"),
    ]
    expected_output_no_hashes = [
        "# Top level requirements",
        "tomli==2.0.1",
        "# Dependencies of top level requirements",
        "pyjokes==0.6.0",
    ]
    actual_output_no_hashes = build_reqirements_file_contents(requirements=mocked_requirements, hashes=False)
    assert expected_output_no_hashes == actual_output_no_hashes
    expected_output_hashes = [
        "# Top level requirements",
        "tomli==2.0.1 \\\n"
        "    --hash=sha256:1234",
        "# Dependencies of top level requirements",
        "pyjokes==0.6.0 \\\n"
        "    --hash=sha256:5678"
    ]
    actual_output_hashes = build_reqirements_file_contents(requirements=mocked_requirements, hashes=True)
    assert expected_output_hashes == actual_output_hashes