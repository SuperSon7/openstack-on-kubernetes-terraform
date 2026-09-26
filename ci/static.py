"""Check scripts and sensitive filenames without changing deployment files."""
import argparse
import fnmatch
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from snapshot import compare

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ("*.tfstate", "*.tfstate.*", "*.tfplan", "*.plan", "*.pem", "*.key",
            "id_rsa*", "id_ed25519*", ".env", ".env.*", "*.tfvars", "*.tfvars.json",
            "credentials", "aws-credentials*", ".terraform.tfstate.lock.info")


def forbidden(path):
    name = PurePosixPath(path).name
    if name == ".env.example":
        return False
    return ".terraform" in PurePosixPath(path).parts or any(
        fnmatch.fnmatch(name, pattern) for pattern in PATTERNS)


def main(update=False):
    os.chdir(ROOT)
    paths = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
    bad = [p for p in paths if p and forbidden(p)]
    if bad:
        raise ValueError("Sensitive runtime files tracked by Git: " + ", ".join(bad))
    scripts = sorted(str(p.relative_to(ROOT)) for folder in ("ci", "osh", "terraform")
                     for p in (ROOT / folder).rglob("*.sh") if ".terraform" not in p.parts)
    for script in scripts:
        subprocess.run(["bash", "-n", script], check=True)
    check = subprocess.run(["shellcheck", "--format=json", *scripts], capture_output=True, text=True)
    if check.returncode not in (0, 1):
        raise ValueError(check.stderr)
    findings = sorted([{k: item[k] for k in ("file", "line", "column", "level", "code", "message")}
                       for item in json.loads(check.stdout)],
                      key=lambda x: (x["file"], x["line"], x["column"], x["code"]))
    reports = Path(os.environ.get("CI_REPORT_DIR", "/tmp/osh-ci-reports"))
    reports.mkdir(parents=True, exist_ok=True)
    actual = reports / "shellcheck.json"
    actual.write_text(json.dumps(findings, indent=2, sort_keys=True) + "\n")
    for item in findings:
        print(f"{item['file']}:{item['line']}: SC{item['code']} ({item['level']}): {item['message']}")
    if any(item["level"] == "error" for item in findings):
        raise ValueError("ShellCheck errors cannot be approved as baseline warnings")
    return compare(ROOT / "tests/baselines/shellcheck.json", actual, reports, update)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true")
    raise SystemExit(main(parser.parse_args().update))
