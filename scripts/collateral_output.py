"""Shared, explicit output policy for collateral builders (standard library only)."""
import argparse
from contextlib import contextmanager
from pathlib import Path
import os
import shutil
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class OutputPlan:
    def __init__(self, parser, args, outputs, project_root):
        self.parser = parser
        self.args = args
        self.protected = (project_root / "website/elh-preview", project_root / "exports")
        self.targets = [
            project_root / approved if args.publish else args.output_dir / proof
            for proof, approved in outputs
        ]
        self.check()

    def check(self):
        for target in self.targets:
            resolved = target.resolve()
            if not self.args.publish and any(
                resolved.is_relative_to(root.resolve()) for root in self.protected
            ):
                self.parser.error(
                    f"Proof output is inside approved website/export paths: {target}. "
                    "Choose an outside directory; use --publish for approved destinations."
                )
            if target.is_symlink() or (
                self.args.publish and any(p.is_symlink() for p in target.parents)
            ):
                self.parser.error(f"Refusing symlink output: {target}")
            if target.exists():
                if not target.is_file():
                    self.parser.error(f"Output is not a regular file: {target}")
                if not self.args.overwrite:
                    self.parser.error(f"Output already exists: {target}. "
                                      "Add --overwrite only if replacement is intentional.")

    @contextmanager
    def stage(self):
        """Nothing reaches final destinations unless the entire build succeeds."""
        with tempfile.TemporaryDirectory(prefix="elh-collateral-stage-") as directory:
            staged = [Path(directory) / f"{i}{p.suffix}"
                      for i, p in enumerate(self.targets)]
            yield staged
            if not all(p.is_file() for p in staged):
                raise RuntimeError("Builder did not produce every planned output")
            self.check()
            for source, target in zip(staged, self.targets):
                target.parent.mkdir(parents=True, exist_ok=True)
                if self.args.overwrite:
                    # Stage on the same filesystem before atomic replacement.
                    fd, name = tempfile.mkstemp(prefix=f".{target.name}-",
                                                dir=target.parent)
                    try:
                        with os.fdopen(fd, "wb") as dest, source.open("rb") as src:
                            shutil.copyfileobj(src, dest)
                        os.replace(name, target)
                    finally:
                        Path(name).unlink(missing_ok=True)
                else:
                    # Exclusive creation also protects files created since preflight.
                    with target.open("xb") as dest, source.open("rb") as src:
                        shutil.copyfileobj(src, dest)
                print(f"wrote {target}")


def output_plan(description, outputs, argv=None, project_root=PROJECT_ROOT):
    """outputs contains (flat proof filename, project-relative approved path)."""
    parser = argparse.ArgumentParser(description=description)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output-dir", type=Path,
                      help="Keep proofs in this directory, outside website/elh-preview and exports.")
    mode.add_argument("--temp-dir", action="store_true",
                      help="Create and print a persistent system temporary directory for proofs.")
    mode.add_argument("--publish", action="store_true",
                      help="Write approved website/export destinations (not a deployment).")
    parser.add_argument("--overwrite", action="store_true",
                        help="Intentionally replace existing outputs; publishing existing assets "
                             "requires both --publish and --overwrite.")
    args = parser.parse_args(argv)
    if args.temp_dir:
        args.output_dir = Path(tempfile.mkdtemp(prefix="elh-collateral-proof-"))
        print(f"Proof directory (kept for review): {args.output_dir}")
    # Several approved mirrors may share one proof filename.
    if not args.publish:
        outputs = list({proof: (proof, approved) for proof, approved in outputs}.values())
    return OutputPlan(parser, args, outputs, Path(project_root))