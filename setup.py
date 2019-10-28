import os.path

from setuptools import find_packages, setup


def read(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    with open(path, "r") as rfile:
        return rfile.read()


metadata = {}
exec(read("quiz/__about__.py"), metadata)


setup(
    name="quiz",
    version=metadata["__version__"],
    description=metadata["__description__"],
    license=metadata["__license__"],
    long_description=read("README.rst") + "\n\n" + read("HISTORY.rst"),
    long_description_content_type='text/plain',
    url="https://github.com/ariebovenberg/quiz",
    author=metadata["__author__"],
    author_email="a.c.bovenberg@gmail.com",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    install_requires=["gentools~=1.1.0", "snug~=2.0.0"],
    keywords=["graphql", "http", "async"],
    python_requires=">=3.5.2",
    packages=find_packages(exclude=("tests", "docs")),
)
