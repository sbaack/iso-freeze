# iso-freeze: Use `pip install --report` to separate pinned requirements for different optional dependencies

**Warning**: The `--report` option of `pip install` is considered experimental. Expect stuff to break after pip updates.

`pip 22.2` introduced the [`pip install --report`](https://pip.pypa.io/en/latest/reference/installation-report/) option, which together with the `--dry-run` and `--ignore-installed` options can be used to resolve requirements without installing them. While the classic `pip freeze` always pins everything installed, this makes it possible to pin requirements independently from your current environment.

`iso-freeze` is an experimental application that uses these new `pip` options to pin requirements. Just specify a `requirements` file or dependencies in your `pyproject.toml` and it uses the output of `pip install --report` to generate pinned `*requirements.txt` files. You can also sync packages installed in your virtual environment with the output of `pip install report`.

This makes `iso-freeze` a very simple version of the `pip-compile` and `pip-sync` commands provided by [`pip-tools`](https://github.com/jazzband/pip-tools). The biggest difference is that is `iso-freeze` does not rely on any `pip` internals.

## Install

The recommended way to install `iso-freeze` is with [`pipx`](https://pypa.github.io/pipx/):

```bash
pipx install iso-freeze
```

However, you can of course install `iso-freeze` in your local venv via pip:

```bash
python -m pip install --upgrade iso-freeze
```

## Usage

You can use `iso-freeze` either with a [PEP621 compatible](https://peps.python.org/pep-0621/) `pyproject.toml` file or with `requirements` files.

Let's assume you're currently in the directory where your `pyproject.toml` file is stored and you want to pin the base dependencies of your project. Simply call:

```bash
iso-freeze
# OR `iso-freeze pyproject.toml` if you like to be explicit
```

Afterwards, your pinned requirements are stored in `requirements.txt`:

```
# Top level requirements
iso-freeze==0.0.11
# Dependencies of top level requirements
tomli==2.0.1
```

If you would like to pin requirements for a specific optional dependency listed in your `pyproject.toml` file, say `dev` dependencies, you can specify it with the `-d/--dependency` flag. Ideally you will use it in combination with the `-o/--output` flag to specify the name and location of the file you want to store the pinned requirements in:

```bash
iso-freeze -d dev -o dev-requirements.txt
# OR `iso-freeze pyproject.toml -d dev -o dev-requirements.txt`
```

For working with requirements files, `iso-freeze` follows the convention established by [`pip-tools`](https://github.com/jazzband/pip-tools) and assumes you store your unpinned top-level requirements in `*requirements.in` files. So if you're currently in the directory that contains your `requirements.in` file, you can also just call the following to create or update your `requirements.txt`:

```bash
iso-freeze
```

Note: If you have both a `requirements.in` and a `pyproject.toml` file in the same directory, `requirements.in` is preferred if `iso-freeze` is called without specifying a file name.

To pin requirements from a different `*requirements.in` file, simply specify it:

```bash
iso-freeze requirements/dev-requirements.in -o requirements/dev-requirements.txt
```

By default, `iso-freeze` will use whatever Python interpreter is currently activate in your shell by calling `python3 -m pip install`. If you need a different version of Python, you can specify it with the `--python/-p` flag:

```bash
iso-freeze pyproject.toml -p python3.11 -o 311-requirements.txt
# Or specify full path if the Python version you need is not in your PATH:
iso-freeze pyproject.toml -p /Library/Frameworks/Python.framework/Versions/3.11/bin/python -o 311-requirements.txt
```

You can pass arguments directly to `pip install` with the `--pip-args` flag:

```bash
iso-freeze dev-requirements.in --pip-args "--upgrade-strategy eager --require-hashes"
```

Please note that by default, `iso-freeze` calls `pip` as follows:

```bash
# If dependencies come from pyproject.toml 
env PIP_REQUIRE_VIRTUALENV=false python_exec -m pip install -q --dry-run --ignore-installed --report - package1 package2
# If dependencies come from a requirements file
env PIP_REQUIRE_VIRTUALENV=false python_exec -m pip install -q --dry-run --ignore-installed --report - -r requirements_file
```

`env PIP_REQUIRE_VIRTUALENV=false` is set to ensure that this command will not fail if `require-virtualenv = true` is set in `pip.conf`. Arguments added with `--pip-args` will be injected after the `install` keyword. Example: Calling `iso-freeze dev-requirements.in --pip-args "--upgrade-strategy eager"` will result in the following command:

```bash
env PIP_REQUIRE_VIRTUALENV=false python3 -m pip install --upgrade-strategy eager -q --dry-run --ignore-installed --report - -r dev-requirements.in
```

### Sync

With the `--sync/-s` flag, `iso-freeze` syncs your current environment with the output of `pip install --report`:

```bash
iso-freeze pyproject.toml -d dev --sync
```

This will remove any packages that are not dependencies of `dev`, install missing packages and update existing packages to match the exact versions provided in the `pip install --report` output.

**Warning**: Be careful when combining the `--sync` and `--python` options. For example:

```bash
iso-freeze pyproject.toml -d dev --sync --python python3.11
```

This command would install your dependencies globally! If used in combination with `--sync`, the `--python` flag should point to the executable of a virtual environment. Using `--sync` without the `--python` flag when no virtual environment is activated will install packages globally too. For security, consider adding `require-virtualenv = true` to your [pip configuration](https://pip.pypa.io/en/stable/topics/configuration/?highlight=require-virtualenv#configuration-files).

Note that `--sync` ignores editable installs.

### Hashes

`iso-freeze` has limited support for adding hashes because `pip install --report` only provides one hash for the exact file used to install a package on your system. You can include hashes with the `--hashes` flag:

```bash
iso-freeze pyproject.toml -d dev --hashes
```

This creates an output like this (truncated example):

```
# Top level requirements
pytest==7.1.2 \
    --hash=sha256:13d0e3ccfc2b6e26be000cb6568c832ba67ba32e719443bfe725814d3c42433c
# Dependencies of top level requirements
attrs==21.4.0 \
    --hash=sha256:2d27e3784d7a565d36ab851fe94887c5eccd6a463168875832a1be79c82828b4
```