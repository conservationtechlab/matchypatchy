"""
Download all wheels for offline installation.
Run this once on a machine with internet access.
"""
import subprocess
import sys
from pathlib import Path

def download_wheels(os, python_version="3.12", platform="win_amd64"):
    """Download wheels for the specified platform"""
    wheels_dir = Path(os) / 'wheels'
    wheels_dir.mkdir(exist_ok=True)
    
    # Download wheels
    subprocess.check_call([
        sys.executable, "-m", "pip", "download",
        "--python-version", python_version.replace(".", ""),
        "--platform", platform,
        "--only-binary=:all:",
        "--no-deps",
        "-r", f"{os}_requirements.txt",
        "-d", str(wheels_dir)
    ])
    
    print(f"✓ Wheels downloaded to {wheels_dir}")
    print(f"Wheels found: {len(list(wheels_dir.glob('*.whl')))}")

if __name__ == "__main__":
    # Download for different platforms
    print("Downloading wheels for Windows (Python 3.12)...")
    download_wheels("windows", python_version="3.12", platform="win_amd64")
    
    print("\nDownloading wheels for Linux (Python 3.12)...")
    download_wheels("linux", python_version="3.12", platform="manylinux_2_28_x86_64")
    
    print("\nDownloading wheels for macOS (Python 3.12)...")
    download_wheels("macos", python_version="3.12", platform="macosx_10_15_x86_64")
    
    print("\n✓ All wheels downloaded successfully!")