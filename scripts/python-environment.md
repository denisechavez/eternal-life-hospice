# Replit-managed Python packages

The supported `python-3.11` module selects `.pythonlibs` as its writable
`uv` project environment. Do not create a second application environment or
point installers into `/nix/store`.

`setup-python-environment.py` runs through `.replit`'s `onBoot` command.
It repairs an incomplete `.pythonlibs` in place with
`uv venv --allow-existing`, using the module's underlying interpreter.
It never clears installed tools. After repair it clears uv's download and
interpreter cache through `uv cache clean`, since a cached prefix can otherwise
continue targeting read-only Nix directories. Healthy starts are a no-op.

Install required runtime dependencies through Replit's package tools as usual.
The site currently needs only the standard library. Pillow remains declared
under the `newsletter` extra because the internal Journal builder uses it.

To sync that explicitly requested extra in the workspace:

```sh
python3 scripts/setup-python-environment.py
uv sync --extra newsletter --inexact
```

`--inexact` preserves other installed internal tools. Plain `uv sync` is an exact
sync and removes packages not selected by the project. Use the default
`uv lock && uv sync` publishing sequence in a fresh deployment environment,
not to maintain a workspace containing unrelated publication tools.

Regression verification:

```sh
python3 scripts/test-python-environment.py
python3 website/test-journal-campaign.py
python3 website/test-resources-journal.py
```

The environment test uses a disposable project with Replit's `.pythonlibs`
layout, primes the bad-prefix cache, repairs it, installs the newsletter extra,
creates a real JPEG and runs the default publishing sequence. Public files and
workspace tools are not changed by these tests.