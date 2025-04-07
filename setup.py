#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="bluecode",
    version="0.1.0",
    description="Privacy and security tools for GL-iNet routers",
    author="GL-iNet",
    packages=find_packages(),
    package_dir={"": "."},
    install_requires=[
        "pyserial",  # For modem communication
    ],
    entry_points={
        "console_scripts": [
            "bluecode=src.cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: System Administrators",
        "Topic :: System :: Networking",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.6",
)
