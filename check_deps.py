"""Check for newer versions of pinned dependencies in pyproject.toml."""

import json
import re
import tomllib
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from packaging.version import Version


@dataclass
class DependencyCheck:
    name: str
    pinned_version: str
    latest_version: str
    has_update: bool
    error: str | None = None


def parse_dependency(dep_string: str) -> tuple[str, str]:
    """Extract package name and version from a dependency string like 'click>=8.3.0'."""
    # Match package name and version specifier
    match = re.match(r"([a-zA-Z0-9_-]+)\s*([><=!~]+)\s*([0-9a-zA-Z._-]+)", dep_string)
    if match:
        return match.group(1), match.group(3)
    # If no version specifier, return just the name
    match = re.match(r"([a-zA-Z0-9_-]+)", dep_string)
    if match:
        return match.group(1), ""
    return dep_string, ""


def get_latest_version(package_name: str) -> str:
    """Query PyPI API to get the latest version of a package."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode())
        return data["info"]["version"]


def check_dependencies(pyproject_path: Path) -> list[dict]:
    """Check all dependencies in pyproject.toml for updates."""
    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    dependencies = pyproject.get("project", {}).get("dependencies", [])
    results = []

    for dep in dependencies:
        name, pinned_version = parse_dependency(dep)
        check = DependencyCheck(
            name=name,
            pinned_version=pinned_version,
            latest_version="",
            has_update=False,
        )

        try:
            latest = get_latest_version(name)
            check.latest_version = latest

            if pinned_version and latest:
                try:
                    check.has_update = Version(latest) > Version(pinned_version)
                except Exception:
                    # Fall back to string comparison if version parsing fails
                    check.has_update = latest != pinned_version
        except Exception as e:
            check.error = str(e)

        results.append({
            "name": check.name,
            "pinned_version": check.pinned_version,
            "latest_version": check.latest_version,
            "has_update": check.has_update,
            "error": check.error,
        })

        # Print progress
        status = "✓ UPDATE" if check.has_update else "  OK" if not check.error else "✗ ERROR"
        print(f"{status}: {name} {pinned_version} -> {check.latest_version or check.error}")

    return results


def main():
    script_dir = Path(__file__).parent
    pyproject_path = script_dir / "pyproject.toml"
    output_path = script_dir / "dependency_updates.json"

    if not pyproject_path.exists():
        print(f"Error: {pyproject_path} not found")
        return

    print(f"Checking dependencies in {pyproject_path}...\n")
    results = check_dependencies(pyproject_path)

    # Save results to JSON
    output = {
        "pyproject_path": str(pyproject_path),
        "dependencies": results,
        "summary": {
            "total": len(results),
            "updates_available": sum(1 for r in results if r["has_update"]),
            "errors": sum(1 for r in results if r["error"]),
        },
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nResults saved to {output_path}")
    print(f"Summary: {output['summary']['updates_available']} updates available out of {output['summary']['total']} dependencies")


if __name__ == "__main__":
    main()


