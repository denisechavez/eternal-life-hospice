#!/usr/bin/env python3
"""Repair Replit's existing managed Python environment without clearing tools."""
from pathlib import Path
import json
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = ROOT / ".pythonlibs"


def environment_prefix():
    interpreter = ENVIRONMENT / "bin" / "python"
    if not interpreter.exists():
        return None
    result = subprocess.run(
        [str(interpreter), "-c", "import json,sys; print(json.dumps(sys.prefix))"],
        capture_output=True, text=True,
    )
    if result.returncode:
        print(f"Managed interpreter needs repair: {result.stderr.strip()}", file=sys.stderr)
        return None
    return Path(json.loads(result.stdout)).resolve()


def main():
    # This is the directory selected by Replit's Python module, not a new
    # application-specific venv. Never clear it: other internal tools live here.
    if environment_prefix() != ENVIRONMENT.resolve():
        # An executable under .pythonlibs can be a link to Replit's wrapper.
        # Passing that link to uv would create a self-referencing interpreter.
        # Use the underlying module interpreter, discovered dynamically so
        # no machine-specific Nix store paths are saved in project config.
        interpreter = Path(sys.base_prefix) / "bin" / f"python{sys.version_info.major}.{sys.version_info.minor}"
        subprocess.run(
            ["uv", "venv", "--allow-existing", "--python", str(interpreter),
             str(ENVIRONMENT)],
            cwd=ROOT, check=True,
        )
        # uv caches interpreter prefixes. Restoring pyvenv.cfg alone leaves
        # a cached /nix/store prefix usable by subsequent package installs.
        # Use uv's supported cache command rather than editing its cache files.
        subprocess.run(["uv", "cache", "clean"], cwd=ROOT, check=True)
    if environment_prefix() != ENVIRONMENT.resolve():
        raise RuntimeError("Replit Python still resolves outside .pythonlibs")
    print("Managed Python environment OK: .pythonlibs")


if __name__ == "__main__":
    main()