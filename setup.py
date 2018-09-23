import os.path

from setuptools import find_packages, setup


def read(fname):
    path = os.path.join(os.path.dirname(__file__), fname)
    with open(path, 'r') as rfile:
        return rfile.read()


metadata = {}
exec(read('quiz/__about__.py'), metadata)


setup(
    name='quiz',
    version=metadata['__version__'],
    description=metadata['__description__'],
    license=metadata['__license__'],
    long_description=read('README.rst') + '\n\n' + read('HISTORY.rst'),
    url='https://github.com/ariebovenberg/quiz',

    author=metadata['__author__'],
    author_email='a.c.bovenberg@gmail.com',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    install_requires=[
        'enum34~=1.1.6; python_version<"3.4"',
        'gentools~=1.1.0',
        'six~=1.11.0',
        'snug~=1.3',
        'typing>=3.6.2; python_version<"3.5"',
    ],
    keywords=['graphql', 'http', 'async'],
    python_requires='>=2.7',
    packages=find_packages(exclude=('tests', 'docs')),
)
