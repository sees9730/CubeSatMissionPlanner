# -*- coding: utf-8 -*-

# CubeSat Mission Planner documentation build configuration file

import sys
import os
from datetime import date

# -- Project information -----------------------------------------------------
project = 'CubeSat Mission Planner'
copyright = f'{date.today().year}, Your Name/Organization'
author = 'Your Name'

# The short X.Y version
version = '0.1'
# The full version, including alpha/beta/rc tags
release = '0.1.0'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension modules here
extensions = [
    'sphinx.ext.autodoc',        # Include documentation from docstrings
    'sphinx.ext.viewcode',       # Add links to the source code
    'sphinx.ext.mathjax',        # Support for math equations
    'sphinx.ext.napoleon',       # Support for NumPy and Google style docstrings
    'sphinx.ext.intersphinx',    # Link to other project's documentation
    'sphinx.ext.todo',           # Support for todo items
]

# Add any paths that contain templates here
templates_path = ['_templates']

# List of patterns to exclude from source files
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The suffix of source filenames
source_suffix = '.rst'

# The master toctree document
master_doc = 'index'

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages
html_theme = 'sphinx_rtd_theme'  # Read the Docs theme

# Theme options
html_theme_options = {
    'navigation_depth': 4,
    'titles_only': False,
}

# Add any paths that contain custom static files
html_static_path = ['_static']

# Output file base name for HTML help builder
htmlhelp_basename = 'CubeSatMissionPlannerdoc'

# -- Extension configuration -------------------------------------------------

# Example configuration for intersphinx
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/reference/', None),
}

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# Todo configuration
todo_include_todos = True

# -- Additional CubeSat-specific settings ------------------------------------

# You can add custom variables here that will be available in your RST files
# For example:
cubesat_types = ['1U', '2U', '3U', '6U', '12U']
orbit_types = ['LEO', 'SSO', 'GEO', 'Lunar', 'Interplanetary']

# If your code has specific modules you want to document:
autodoc_member_order = 'bysource'
autoclass_content = 'both'  # Include both class and __init__ docstrings