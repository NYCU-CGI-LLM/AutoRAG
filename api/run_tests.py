#!/usr/bin/env python3
"""
Test runner script for API tests
"""
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", verbose=False, coverage=False, parallel=False):
    """Run tests with specified options"""
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test paths based on type
    if test_type == "unit":
        cmd.append("tests/unit/")
    elif test_type == "integration":
        cmd.append("tests/integration/")
    elif test_type == "all":
        # Only include unit and integration tests, exclude archived
        cmd.extend(["tests/unit/", "tests/integration/"])
    else:
        cmd.append(f"tests/{test_type}/")
    
    # Add options
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
    
    if parallel:
        cmd.extend(["-n", "auto"])
    
    # Add markers for specific test types
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    
    print(f"Running command: {' '.join(cmd)}")
    return subprocess.run(cmd)


def install_test_dependencies():
    """Install test dependencies"""
    print("Installing test dependencies...")
    return subprocess.run([
        "uv", "pip", "install", "-r", "requirements-test.txt"
    ])


def main():
    parser = argparse.ArgumentParser(description="Run API tests")
    parser.add_argument(
        "test_type",
        choices=["all", "unit", "integration", "services", "models", "api"],
        default="all",
        nargs="?",
        help="Type of tests to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Run with coverage"
    )
    parser.add_argument(
        "-p", "--parallel",
        action="store_true",
        help="Run tests in parallel"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install test dependencies first"
    )
    
    args = parser.parse_args()
    
    if args.install_deps:
        result = install_test_dependencies()
        if result.returncode != 0:
            print("Failed to install dependencies")
            sys.exit(1)
    
    result = run_tests(
        test_type=args.test_type,
        verbose=args.verbose,
        coverage=args.coverage,
        parallel=args.parallel
    )
    
    sys.exit(result.returncode)


if __name__ == "__main__":
    main() 