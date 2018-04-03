import os.path
from setuptools import setup, find_packages


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
    license='MIT',
    long_description=read('README.rst') + '\n\n' + read('HISTORY.rst'),
    url='https://github.com/ariebovenberg/quiz',

    author=metadata['__author__'],
    author_email='a.c.bovenberg@gmail.com',

    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    install_requires=[
        'typing>=3.6.2 ; python_version<"3.5"',
    ],
    keywords=['graphql', 'http', 'async', 'graphql'],
    python_requires='>=2.7',
    packages=find_packages(exclude=('examples', 'tests', 'docs', 'tutorial')),
)
