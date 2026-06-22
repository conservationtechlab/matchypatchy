"""
Download all wheels for offline installation.
Run this once on a machine with internet access.
"""
import argparse
import subprocess
import sys
from pathlib import Path

def download_wheels(requirements, python_version="3.12", platform="win_amd64"):
    """Download wheels for the specified platform"""
    wheels_dir = Path('new_wheels')
    wheels_dir.mkdir(exist_ok=True)
    
    # Download wheels
    subprocess.check_call([
        sys.executable, "-m", "pip", "download",
        "--python-version", python_version.replace(".", ""),
        "--platform", platform,
        "--only-binary=:all:",
        "--no-deps",
        "-r", requirements,
        "-d", str(wheels_dir)
    ])
    
    print(f"✓ Wheels downloaded to {wheels_dir}")
    print(f"Wheels found: {len(list(wheels_dir.glob('*.whl')))}")

if __name__ == "__main__":
    # Download for different platforms
    parser = argparse.ArgumentParser()

    # 2. Add a positional argument (required by default)
    parser.add_argument(
        "requirements_file", 
        help="The path to the file you want to process."
    )

    parser.add_argument(
        "platform", 
        help="The platform for which to download wheels (e.g., win_amd64, manylinux_2_28_x86_64, macosx_10_15_x86_64)."
    )


    # 3. Add an optional argument with a default value and specific type
    parser.add_argument(
        "-p", "--python_version", 
        type=str, 
        default="3.12", 
        help="Python version to use (default: 3.12)."
    )

    # 4. Add a boolean flag (True if present, False if absent)

    # 5. Parse the arguments
    args = parser.parse_args()

    download_wheels(args.requirements_file, python_version=args.python_version, platform=args.platform)

    print("\n✓ All wheels downloaded successfully!")