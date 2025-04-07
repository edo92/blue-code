from setuptools import setup, find_packages

setup(
    name="bluecode-security",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "pyserial>=3.5",
    ],
    entry_points={
        'console_scripts': [
            'bluecode=bluecode.cli:main',
        ],
    },
    include_package_data=True,
    package_data={
        'bluecode': ['data/templates/*', 'data/scripts/*'],
    },
    scripts=[
        'scripts/bluecode-service',
    ],
    python_requires='>=3.6',
    description="BlueCode Security Tools to enhance anonymity and reduce forensic traceability",
    author="GL-iNet",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Topic :: Security",
        "Topic :: System :: Networking",
    ],
)
