#!/usr/bin/env python3
"""
Script to run tests with different options.
"""

import subprocess
import sys


def run_tests(test_type="all"):
    """Run tests with specified options."""

    base_cmd = ["python", "-m", "pytest", "-v"]

    if test_type == "all":
        cmd = base_cmd + ["tests/"]
    elif test_type == "unit":
        cmd = base_cmd + ["-m", "unit", "tests/"]
    elif test_type == "api":
        cmd = base_cmd + ["-m", "api", "tests/"]
    elif test_type == "coverage":
        cmd = base_cmd + ["--cov=src/pydocs", "--cov-report=html", "tests/"]
    else:
        cmd = base_cmd + [test_type]

    print(f"Running command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        return result.returncode == 0
    except FileNotFoundError:
        print("Error: pytest not found. Please install it with 'pip install pytest'")
        return False
    except Exception as e:
        print(f"Error running tests: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
    else:
        test_type = "all"

    success = run_tests(test_type)
    sys.exit(0 if success else 1)
