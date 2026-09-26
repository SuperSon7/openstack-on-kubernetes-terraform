"""Compare reviewed snapshots; baseline updates are explicit local operations."""
import argparse
import difflib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compare(expected_path, actual_path, report_dir, update=False):
    actual = actual_path.read_text()
    if update:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise ValueError("CI must not approve its own snapshot changes")
        expected_path.parent.mkdir(parents=True, exist_ok=True)
        expected_path.write_text(actual)
        print(f"Updated {expected_path}; review and commit with the code change.")
        return 0
    expected = expected_path.read_text() if expected_path.exists() else ""
    difference = "".join(difflib.unified_diff(
        expected.splitlines(True), actual.splitlines(True),
        fromfile=f"approved/{expected_path.name}", tofile=f"generated/{actual_path.name}"))
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / (actual_path.stem + ".diff")).write_text(difference)
    (report_dir / actual_path.name).write_text(actual)
    status = "CHANGED: review the diff and update the baseline" if difference else "MATCH"
    print(f"{actual_path.stem}: {status}")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a") as summary:
            summary.write(f"### {actual_path.stem}\n\n{status}\n\n")
            if difference:
                summary.write("Full diff is in the report artifact.\n\n```diff\n"
                              + difference[:16000] + "\n```\n")
    if difference:
        print(difference[:16000])
    return int(bool(difference))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=["terraform", "helm", "shellcheck"])
    parser.add_argument("actual", type=Path)
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()
    baseline_dir = "baselines" if args.name == "shellcheck" else "snapshots"
    report_dir = Path(os.environ.get("CI_REPORT_DIR", "/tmp/osh-configuration-ci/reports"))
    raise SystemExit(compare(ROOT / "tests" / baseline_dir / f"{args.name}.json",
                             args.actual, report_dir, args.update))
