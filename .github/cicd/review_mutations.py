"""Isolated baseline -> new API -> existing regression. Never uses project .env."""
import argparse
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / ".ci-results" / "mutations"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--postgresql", action="store_true", help="Require disposable RACE_TEST_DB_URL")
    parser.add_argument("--base-ref", default="HEAD", help="Immutable comparison base, default HEAD")
    args = parser.parse_args()
    REPORT.mkdir(parents=True, exist_ok=True)
    baseline = REPORT / "baseline"
    baseline.mkdir(exist_ok=True)
    base_commit = subprocess.check_output(["git", "rev-parse", "--verify", "--end-of-options", args.base_ref + "^{commit}"], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(["git", "archive", "--format=zip", base_commit, "api", ".github/cicd"], cwd=ROOT)
    with zipfile.ZipFile(io.BytesIO(archive)) as source:
        source.extractall(baseline)
    report = {"base_commit": base_commit,
              "backend": "postgresql" if args.postgresql else "sqlite", "stages": []}
    with tempfile.TemporaryDirectory(prefix="edufast-mutations-") as folder:
        url = os.environ.get("RACE_TEST_DB_URL") if args.postgresql else "sqlite:///" + (Path(folder) / "tests.sqlite").as_posix()
        if args.postgresql:
            from sqlalchemy.engine import make_url
            parsed = make_url(url or "")
            if parsed.get_backend_name() != "postgresql" or not (parsed.database or "").startswith("race_ci_"):
                raise RuntimeError("PostgreSQL database name must start with race_ci_; use an empty disposable DB")
        env = {**os.environ, "DB_URL": url, "EDUFAST_TEST_DISPOSABLE": "1",
               "APP_ENV": "testing", "SECRET_KEY": "synthetic-test-secret-with-at-least-32-characters",
               "UPLOAD_FOLDER": str(Path(folder) / "uploads"), "PYTHONIOENCODING": "utf-8",
               "PYTHONDONTWRITEBYTECODE": "1", "PYTHON_DOTENV_DISABLED": "1"}
        stages = [("baseline-existing", baseline, "test_application.py"),
                  ("new-api", ROOT, "test_concurrency.py"),
                  ("regression-existing", ROOT, "test_application.py")]
        for name, checkout, pattern in stages:
            env["PYTHONPATH"] = str(checkout / "api") + os.pathsep + os.environ.get("PYTHONPATH", "")
            result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s",
                                     str(checkout / ".github/cicd/tests"), "-p", pattern, "-v"],
                                    env=env, cwd=folder, capture_output=True)
            log = result.stdout + result.stderr
            (REPORT / f"{name}-{report['backend']}.log").write_bytes(log)
            print(log.decode("utf-8", errors="replace"), flush=True)
            report["stages"].append({"name": name, "passed": result.returncode == 0})
            if result.returncode:
                break
    report["passed"] = len(report["stages"]) == 3 and all(s["passed"] for s in report["stages"])
    (REPORT / f"summary-{report['backend']}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
