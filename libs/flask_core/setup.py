"""
Setup configuration for Waddles Flask Core Library
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# install_requires must stay abstract (PEP 508 specifiers only) -- read the
# loose requirements.in, not the hash-annotated requirements.txt. The hashed
# requirements.txt is for `pip install -r --require-hashes` reproducibility
# only; its `--hash=...` continuation lines are not valid requirement
# specifiers and break setuptools' install_requires validation.
with open("requirements.in", "r", encoding="utf-8") as fh:
    requirements = [
        line.split("#", 1)[0].strip()
        for line in fh
        if line.strip() and not line.strip().startswith("#")
    ]
    requirements = [r for r in requirements if r]

setup(
    name="waddlebot-flask-core",
    version="2.0.0",
    author="Waddles Team",
    author_email="team@waddlebot.com",
    description="Shared utilities for Waddles Flask/Quart modules",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/waddlebot/waddlebot",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Framework :: Flask",
        "Framework :: Quart",
    ],
    python_requires=">=3.12",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
            "black>=23.12.0",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
