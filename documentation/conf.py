# -*- coding: utf-8 -*-
#
# GlobaLeaks documentation build configuration file.
#
import gettext
import glob
import hashlib
import os
import pathlib
import re
import shutil
import sys

from docutils import nodes
from docutils.parsers.rst import roles

sys.path.append(os.path.abspath('./_ext'))
sys.path.insert(0, os.path.abspath('../backend'))

from globaleaks import __author__,  __copyright__, __version__

base_dir = os.path.dirname(__file__)

autodoc_member_order = 'bysource'

autodoc_default_options = {
    'members': True,
    'show-inheritance': True,
    'undoc-members': True,
}

extensions = [
  'sphinx_copybutton',
  'sphinx_sitemap',
  'sphinx.ext.imgconverter'
]

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

project = __author__
copyright = __copyright__
author = __author__
version = __version__
release = __version__

language = 'en'
language = os.environ.get('READTHEDOCS_LANGUAGE', language)

locale_dirs = ['locale/']
locale_dir = os.path.join(os.path.dirname(__file__), locale_dirs[0])
gettext.bindtextdomain('sphinx', locale_dir)
gettext.textdomain('sphinx')
gettext_compact = 'sphinx'

exclude_patterns = ['_build']
show_authors = False
pygments_style = 'sphinx'

html_theme = 'furo'
html_baseurl = 'https://docs.globaleaks.org/'
html_favicon = '../client/app/images/favicon.ico'
html_show_copyright = False
htmlhelp_basename = 'globaleaks'
html_static_path = ['_static']

html_context = {
  'description': 'GlobaLeaks is free, open souce whistleblowing software enabling anyone to easily set up and maintain a secure reporting platforms',
  'keywords': 'globaleaks, whistleblowing, globaleaks-whistleblowing-software',
  'author': 'GLOBALEAKS',
  'display_github': True,
  'github_user': 'globaleaks',
  'github_repo': 'globaleaks-whistleblowing-software',
  'github_version': 'main',
  'conf_py_path': '/documentation/'
}

# --- Furo theme options -----------------------------------------------------
html_theme_options = {
    "source_repository": "https://github.com/globaleaks/globaleaks-whistleblowing-software",
    "source_branch": "stable",
    "source_directory": "documentation/",
    "html_show_sourcelink": False,
    "html_copy_source": False,
    "light_logo": "images/logo-light-html.webp",
    "dark_logo": "images/logo-dark-html.webp",
    "light_css_variables": {
        "color-brand-primary": "#205282",
        "color-brand-content": "#205282",
    },
    "dark_css_variables": {
        "color-brand-primary": "#79B0E6",
        "color-brand-content": "#79B0E6",
    },
}

latex_elements = {
  'preamble': r'\pdfmapfile{+"../../texmf/fonts/map/dvips/fontawesome7/fontawesome7.map"}',
  'sphinxsetup': 'InnerLinkColor={HTML}{205282}, OuterLinkColor={HTML}{205282}, iconpackage=fontawesome7',
}

latex_documents = []

latex_logo = 'images/logo-latex.pdf'

man_pages = [
    (master_doc, 'globaleaks', 'GlobaLeaks Documentation', [author], 1)
]

texinfo_documents = [
    (master_doc, 'GLOBALEAKS', 'GlobaLeaks Documentation',
     author, 'GLOBALEAKS',
     'GlobaLeaks is free, open source whistleblowing software enabling anyone to easily set up and maintain a secure reporting platform',
     'Miscellaneous'),
]

def fa_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
    """
    Role :fa:`regular address-book` → \faIcon[regular]{address-book}
    Role :fa:`solid circle-info`   → \faIcon[solid]{circle-info}
    Role :fa:`address-book`        → \faIcon{address-book}
    """
    parts = text.strip().split()
    if len(parts) == 2:
        style, icon = parts
        latex_code = f"\\faIcon[{style}]{{{icon}}}"
        html_code = f'<i class="fa-{style} fa-{icon}"></i>'
    else:
        # default to solid style
        icon = parts[0] if parts else "question"
        latex_code = f"\\faIcon{{{icon}}}"
        html_code = f'<i class="fa-solid fa-{icon}"></i>'

    node = nodes.raw('', latex_code, format='latex')
    html_node = nodes.raw('', html_code, format='html')
    return [node, html_node], []


def update_install_hash(app, docname, source):
    # Keep the install.sh checksum published in the installation guide in sync
    # with the actual script at build time.
    if docname != 'setup/installation':
        return

    install_script = os.path.join(base_dir, '..', 'scripts', 'install.sh')
    with open(install_script, 'rb') as f:
        digest = hashlib.sha256(f.read()).hexdigest()

    source[0], n = re.subn(r'[0-9a-f]{64}(\s+install\.sh)', digest + r'\1', source[0])
    if n != 1:
        raise ValueError("install.sh checksum placeholder not found in setup/installation")


def setup(app):
    # register our local :fa: role
    roles.register_local_role('fa', fa_role)
    app.connect('source-read', update_install_hash)
    translation = gettext.translation('sphinx', localedir=locale_dir, languages=[app.config.language], fallback=True)
    document_title = translation.gettext('Documentation')
    app.config.latex_documents = [(master_doc, 'GlobaLeaks.tex', document_title, '', 'manual'),]

    app.add_css_file("custom.css")
    app.add_css_file("fa7/css/all.min.css")
    app.add_js_file("custom.js")
