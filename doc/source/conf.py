#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# podpac documentation build configuration file, created by
# sphinx-quickstart on Fri May 11 12:40:16 2018.
#
# This file is execfile()d with the current directory set to its
# containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
import datetime

# for parsing markdown files
# pip install recommonmark
from recommonmark.parser import CommonMarkParser
from recommonmark.transform import AutoStructify
source_parsers = {
    '.md': CommonMarkParser,
}

GIT_URL = 'https://github.com/creare-com/podpac'

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'numpydoc',
    'sphinx.ext.todo',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.extlinks',
    'sphinx.ext.githubpages',
    'sphinx.ext.doctest'
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
source_suffix = ['.rst', '.md']

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'PODPAC'
copyright = '2017-{}, Creare'.format(datetime.datetime.now().year)
author = 'Creare'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.0.0'
# The full version, including alpha/beta/rc tags.
release = '0.0.0'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = []

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# see https://numpydoc.readthedocs.io/en/latest/install.html
numpydoc_class_members_toctree = True
numpydoc_show_class_members = False
numpydoc_show_inherited_class_members = False

# generate autosummary files into the :toctree: directory
# see http://www.sphinx-doc.org/en/master/ext/autosummary.html
autosummary_generate = True

# autodoc options
autodoc_default_flags = ['members']  # deprecated in sphinx 1.8

# shortened external links. see http://www.sphinx-doc.org/en/master/ext/extlinks.html
extlinks = {'issue': ('{0}/issues/%s'.format(GIT_URL), '#'), # refer to issues :issue:`123`
            'github': ('{0}'.format(GIT_URL), '')}

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
html_theme_options = {
    'canonical_url': 'https://creare-com.github.io/podpac-docs',
    'logo_only': True
}


# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
html_logo = "_static/img/icon.png"
html_favicon = "_static/img/favicon.png"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']



# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'podpacdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',

    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, 'podpac.tex', 'podpac Documentation',
     'Creare', 'manual'),
]


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    (master_doc, 'podpac', 'podpac Documentation',
     [author], 1)
]


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (master_doc, 'podpac', 'podpac Documentation',
     author, 'podpac', 'One line description of project.',
     'Miscellaneous'),
]


# -- app setup -------------------------------------------

def setup(app):
    app.add_stylesheet('style.css')  # may also be an URL
