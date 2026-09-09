"""Setup configuration for the Waddles content-moderation classifier library."""

from setuptools import find_packages, setup

# install_requires must stay abstract (PEP 508 specifiers only) -- read the
# loose requirements.in, not the hash-annotated requirements.txt. Mirrors
# libs/waddle_transports/setup.py's own rationale (see that file's comment).
with open("requirements.in", encoding="utf-8") as fh:
    requirements = [
        line.split("#", 1)[0].strip()
        for line in fh
        if line.strip() and not line.strip().startswith("#")
    ]
    requirements = [r for r in requirements if r]

setup(
    name="waddlebot-moderation",
    version="0.1.0",
    author="Waddles Team",
    author_email="team@waddlebot.com",
    description=(
        "Pluggable content-moderation classification (ClassificationProvider "
        "contract + LocalOllamaClassifier, the Basic-tier ShieldGemma provider) "
        "for Waddles pipeline-stage services"
    ),
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.13",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
