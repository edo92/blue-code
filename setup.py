from setuptools import setup, find_packages

setup(
    name="blue-code",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "pyserial",
    ],
    entry_points={
        'console_scripts': [
            'blue-code=src.cli:main',
        ],
    },
    python_requires='>=3.6',
    description="BlueCode Security Tools to enhance anonymity and reduce forensic traceability",
    author="GL-iNet",
)
