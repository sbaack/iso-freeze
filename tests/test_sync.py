from iso_freeze.sync import *


def test_get_installed_packages():
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
        PyPackage(name="attrs", version="21.4.0", requested=False, hash=None),
        PyPackage(name="iniconfig", version="1.1.1", requested=False, hash=None),
        PyPackage(name="iso-freeze", version="0.0.10", requested=False, hash=None),
        PyPackage(name="packaging", version="21.3", requested=False, hash=None),
        PyPackage(name="pip", version="22.2", requested=False, hash=None),
        PyPackage(name="pluggy", version="1.0.0", requested=False, hash=None),
    ]
    actual_output = get_installed_packages(mocked_pip_list_output)
    assert actual_output == expected_output


def test_get_additional_packages():
    """Test if additional packages are properly detected and removed."""
    mocked_pip_list_output = [
        PyPackage(name="tomli", version="2.0.1", requested=False, hash=None),
        # Two packages not in mocked pip report output
        PyPackage(name="pip", version="22.2", requested=False, hash=None),
        PyPackage(name="cowsay", version="5.0", requested=False, hash=None),
    ]
    mocked_pip_report_output = [
        PyPackage(name="tomli", version="2.0.1", requested=True, hash="sha256:1234"),
        # One package not in mocked pip list output
        PyPackage(name="pyjokes", version="0.6.0", requested=True, hash="sha256:5678"),
    ]
    to_delete = get_additional_packages(
        installed_packages=mocked_pip_list_output,
        to_install=mocked_pip_report_output,
    )
    # pip should not be removed, cowsay should
    assert to_delete == ["cowsay"]


def test_format_package_list():
    """Test if pip report --install output is properly passed to pip install."""
    mocked_pip_report_output = [
        PyPackage(name="tomli", version="2.0.1", requested=True, hash="sha256:1234"),
        PyPackage(name="pyjokes", version="0.6.0", requested=True, hash="sha256:5678"),
    ]
    expected_output = ["tomli==2.0.1", "pyjokes==0.6.0"]
    actual_output = format_package_list(packages=mocked_pip_report_output)
    assert expected_output == actual_output