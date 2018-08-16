# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import quiz  # noqa


# -- Project information -----------------------------------------------------

project = quiz.__name__.title()
copyright = quiz.__copyright__
author = quiz.__author__

# The short X.Y version
version = quiz.__version__
# The full version, including alpha/beta/rc tags
release = quiz.__version__


# -- General configuration ---------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'manni'
# pygments_style = 'sphinx'
pygments_style = 'default'

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'alabaster'

highlight_language = 'python3'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
    "description": quiz.__doc__,
    'description_font_style': 'italic',
    "github_user": 'ariebovenberg',
    "github_repo": 'quiz',
    "github_banner": True,
    'codecov_button': True,
    "github_type": 'star',
    'fixed_sidebar': True,
    'code_font_size': '0.8em',
    'travis_button': True,

    'note_bg': '#DAF2ED',
    'note_border': '#DAF2ED',
    'warn_bg': '#FFE8E8',
    'warn_border': '#FFE8E8',
    'pre_bg': '#E8EDDF',
}

html_sidebars = {
    '**': ['about.html', 'navigation.html', 'searchbox.html']
}


# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'snug': ('https://snug.readthedocs.org/en/latest/', None),
}
