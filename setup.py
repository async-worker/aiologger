from collections import OrderedDict

import setuptools
from setuptools import setup, find_packages

VERSION = "0.6.0"

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="aiologger",
    version=VERSION,
    packages=find_packages(exclude=["*test*"]),
    description="Asynchronous logging for python and asyncio",
    long_description=long_description,
    long_description_content_type="text/markdown",
    license="MIT",
    python_requires=">=3.6",
    extras_require={"aiofiles": ["aiofiles==0.4.0"]},
    url="https://github.com/b2wdigital/aiologger",
    project_urls=OrderedDict(
        (
            ("Documentation", "https://aiologger.readthedocs.io/en/latest/"),
            ("Code", "https://github.com/b2wdigital/aiologger"),
            ("Issue tracker", "https://github.com/b2wdigital/aiologger/issues"),
        )
    ),
    tests_require=[
        "pytest",
        "pytest-cov",
        "codecov",
        "asynctest==0.12.0",
        "freezegun==0.3.10",
        "mypy==0.630",
        "black==18.9b0",
        "ipdb==0.11",
        "aiofiles==0.4.0",
        "uvloop==0.11.3",
    ],
    author="Diogo Magalhães Martins",
    author_email="magalhaesmartins@icloud.com",
    keywords="logging json log output",
    setup_requires=["setuptools>=38.6.0"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: AsyncIO",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Intended Audience :: System Administrators",
        "Intended Audience :: Information Technology",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Unix",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: System :: Logging",
        "Topic :: Software Development :: Libraries",
    ],
)
