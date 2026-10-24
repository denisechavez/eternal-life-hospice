#!/usr/bin/env python3
"""Non-blocking advisory report. This command never edits website content."""
import argparse
import html
import json
from pathlib import Path
import sys
import traceback

from prepublish_seo import plain_report, run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-dir", type=Path,
                        help="Optional private output folder, outside the public website.")
    args = parser.parse_args()
    try:
        if args.report_dir:
            public = (Path(__file__).resolve().parent / "elh-preview").resolve()
            if args.report_dir.resolve().is_relative_to(public):
                raise ValueError("SEO reports must stay outside the public website.")
        result = run()
        report = plain_report(result)
        print(report)
        if args.report_dir:
            args.report_dir.mkdir(parents=True, exist_ok=True)
            (args.report_dir / "prepublish-seo-report.txt").write_text(report)
            (args.report_dir / "prepublish-seo-report.json").write_text(json.dumps(result, indent=2))
            (args.report_dir / "prepublish-seo-report.html").write_text(
                '<!doctype html><html lang="en"><meta charset="utf-8">'
                '<meta name="viewport" content="width=device-width,initial-scale=1">'
                '<title>Pre-publish SEO report</title><style>'
                'body{background:#f5f0eb;color:#3c1c3b;margin:0;padding:30px}'
                'pre{max-width:1100px;margin:auto;font:16px/1.65 system-ui;'
                'white-space:pre-wrap;overflow-wrap:anywhere}</style>'
                '<pre>' + html.escape(report) + '</pre></html>')
    except Exception:
        print("SEO ADVISORY WARNING: The check could not finish. Publishing is NOT blocked.",
              file=sys.stderr)
        traceback.print_exc()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
