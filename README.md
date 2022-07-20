# iso-freeze: Call pip freeze in an isolated venv

`pip freeze` will always pin everything installed in your current venv, so if you want to pin only your `doc` but not your `dev` requirements, you best create a fresh environment. `iso-freeze` allows you to pin requirements independently from your current environment: you just specify a `requirements` file or an optional dependency in your `pyproject.toml` and it automatically creates a temporary venv, installs all necessary requirements in it and generates pinned `*requirements.txt` files from it.

`iso-freeze` is a very simple version of the `pip-compile` command provided by [`pip-tools`](https://github.com/jazzband/pip-tools). The biggest difference is that is `iso-freeze` does not rely on any `pip` internals and just calls plain `pip freeze` in the background.

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

Afterwards, your pinned requirements are stored in `requirements.txt`.

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

## Passing arguments to pip

You can pass arguments directly to `pip install` and `pip freeze` with the `--install-args` and `freeze-args` flags:

```bash
iso-freeze dev-requirements.in --install-args "--upgrade-strategy eager --require-hashes"
iso-freeze pyproject.toml --freeze-args "--exclude cowsay"
# Or both
iso-freeze dev-requirements.in --install-args "--upgrade-strategy eager" --freeze-args "--exclude cowsay"
```

Please note that `iso-freeze` will call `pip freeze` with the `-r <requiements-file>` flag by default if a requirements file is used as input _unless_ you pass the `--exclude <package>` flag via `--freeze-args`. If both the `-r <requirements-file>` and the `--exclude` flags are used, the `--exclude` flag might be negated if the excluded package is explicitly mentioned in the specified requirements file. To avoid unexpected outcomes, `iso-freeze` won't add any additional flags if `--exclude` is passed to `pip freeze` via `--freeze-args`.
