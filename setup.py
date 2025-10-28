from pathlib import Path
from setuptools import setup, find_packages

HERE = Path(__file__).parent
README_PATH = HERE / "README.md"
long_description = README_PATH.read_text(encoding="utf-8") if README_PATH.exists() else ""

setup(
    name="matchypatchy",
    version="0.1.0",
    author="Kyra Swanson",
    author_email="tswanson@sdzwa.org",
    description="GUI tool for human validation of AI-powered animal re-identification",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/onservationtechlab/matchypatchy",
    project_urls={
        "Homepage": "https://github.com/onservationtechlab/matchypatchy",
        "Issues": "https://github.com/onservationtechlab/matchypatchy/issues",
    },
    packages=find_packages(exclude=("tests", "docs")),
    include_package_data=True,
    python_requires=">=3.9",
    setup_requires=["setuptools>=61.0"],
    install_requires=[
        "animl>=3.0.1",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Operating System :: OS Independent",
    ],
)