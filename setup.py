import os.path
from pathlib import Path

from setuptools import find_packages, setup


def read(fname):
    return (Path(__file__).parent / fname).read_text()


metadata = {}
exec(read("quiz/__about__.py"), metadata)


setup(
    name="quiz",
    version=metadata["__version__"],
    description=metadata["__description__"],
    license=metadata["__license__"],
    long_description=read("README.rst") + "\n\n" + read("HISTORY.rst"),
    long_description_content_type="text/plain",
    url="https://github.com/ariebovenberg/quiz",
    author=metadata["__author__"],
    author_email="a.c.bovenberg@gmail.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    install_requires=[
        "dataclasses==0.7; python_version<'3.7'",
        "gentools~=1.1.0",
        "snug~=2.0.0",
    ],
    keywords=["graphql", "http", "async"],
    python_requires=">=3.6.0",
    packages=find_packages(exclude=("tests", "docs")),
)
