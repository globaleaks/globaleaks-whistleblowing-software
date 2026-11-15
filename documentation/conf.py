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
# The code is told apart by bold and italic alone: the colors of every other Pygments style fall
# under 7:1 on the code surfaces of the palette, in the light or in the dark theme
pygments_style = 'bw'
pygments_dark_style = 'bw'

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
    # The roles of the interface (client/app/css/theme.css) on the official palette of the Visual
    # Identity Guidelines v3.0: every text pair is 7:1 or more (AAA)
    "light_css_variables": {
        "color-brand-primary": "#025A9F",
        "color-brand-content": "#025A9F",
        "color-brand-visited": "#025A9F",
        "color-link--hover": "#002445",
        "color-link--visited--hover": "#002445",
        "color-foreground-primary": "#1F1F1F",
        "color-foreground-secondary": "#525964",
        "color-foreground-muted": "#525964",
        "color-foreground-border": "#6E7783",
        "color-background-primary": "#FFFFFF",
        "color-background-secondary": "#F2F4F7",
        "color-background-hover": "#ECF5FE",
        "color-background-border": "#A5ACB6",
        "color-code-background": "#ECF5FE",
        "color-code-foreground": "#1F1F1F",
        # On the subtle surface of the sidebar (Gray_1) the link is Brand_2
        "color-sidebar-link-text--top-level": "#002445",
        # The rest of the colors of Furo, on the palette: the subtle surface (Blue_1) for the target
        # of a link, the results of the search and the labels; the accent (Blue_3) for the icons of
        # the notes, the red for those of the warnings
        "color-background-hover--transparent": "#ECF5FE00",
        "color-background-item": "#A5ACB6",
        "color-highlight-on-target": "#ECF5FE",
        "color-highlighted-background": "#ECF5FE",
        "color-guilabel-background": "#ECF5FE",
        "color-guilabel-border": "#A5ACB6",
        "color-problematic": "#E30310",
        "color-admonition-background": "transparent",
        "color-card-background": "transparent",
        "color-admonition-title": "#0978CF",
        "color-admonition-title-background": "#ECF5FE",
        "color-topic-title": "#0978CF",
        "color-topic-title-background": "#ECF5FE",
        "color-admonition-title--note": "#0978CF",
        "color-admonition-title-background--note": "#ECF5FE",
        "color-admonition-title--seealso": "#0978CF",
        "color-admonition-title-background--seealso": "#ECF5FE",
        "color-admonition-title--tip": "#0978CF",
        "color-admonition-title-background--tip": "#ECF5FE",
        "color-admonition-title--hint": "#0978CF",
        "color-admonition-title-background--hint": "#ECF5FE",
        "color-admonition-title--important": "#0978CF",
        "color-admonition-title-background--important": "#ECF5FE",
        "color-admonition-title--admonition-todo": "#0978CF",
        "color-admonition-title-background--admonition-todo": "#ECF5FE",
        "color-admonition-title--caution": "#E30310",
        "color-admonition-title-background--caution": "#ECF5FE",
        "color-admonition-title--warning": "#E30310",
        "color-admonition-title-background--warning": "#ECF5FE",
        "color-admonition-title--danger": "#E30310",
        "color-admonition-title-background--danger": "#ECF5FE",
        "color-admonition-title--attention": "#E30310",
        "color-admonition-title-background--attention": "#ECF5FE",
        "color-admonition-title--error": "#E30310",
        "color-admonition-title-background--error": "#ECF5FE",
    },
    "dark_css_variables": {
        "color-brand-primary": "#7BBBFE",
        "color-brand-content": "#7BBBFE",
        "color-brand-visited": "#7BBBFE",
        "color-link--hover": "#ECF5FE",
        "color-link--visited--hover": "#ECF5FE",
        "color-foreground-primary": "#F2F4F7",
        "color-foreground-secondary": "#A5ACB6",
        "color-foreground-muted": "#A5ACB6",
        "color-foreground-border": "#6E7783",
        "color-background-primary": "#1F1F1F",
        "color-background-secondary": "#002445",
        "color-background-hover": "#002445",
        "color-background-border": "#525964",
        "color-code-background": "#002445",
        "color-code-foreground": "#F2F4F7",
        # On the subtle surface of the sidebar (Brand_2) the link keeps Blue_2 (7:1)
        "color-sidebar-link-text--top-level": "#7BBBFE",
        "color-background-hover--transparent": "#00244500",
        "color-background-item": "#525964",
        "color-highlight-on-target": "#002445",
        "color-highlighted-background": "#002445",
        "color-guilabel-background": "#002445",
        "color-guilabel-border": "#525964",
        "color-problematic": "#FF8F90",
        "color-admonition-background": "transparent",
        "color-card-background": "transparent",
        "color-card-marginals-background": "#002445",
        "color-admonition-title": "#0978CF",
        "color-admonition-title-background": "#002445",
        "color-topic-title": "#0978CF",
        "color-topic-title-background": "#002445",
        "color-admonition-title--note": "#0978CF",
        "color-admonition-title-background--note": "#002445",
        "color-admonition-title--seealso": "#0978CF",
        "color-admonition-title-background--seealso": "#002445",
        "color-admonition-title--tip": "#0978CF",
        "color-admonition-title-background--tip": "#002445",
        "color-admonition-title--hint": "#0978CF",
        "color-admonition-title-background--hint": "#002445",
        "color-admonition-title--important": "#0978CF",
        "color-admonition-title-background--important": "#002445",
        "color-admonition-title--admonition-todo": "#0978CF",
        "color-admonition-title-background--admonition-todo": "#002445",
        "color-admonition-title--caution": "#FF8F90",
        "color-admonition-title-background--caution": "#002445",
        "color-admonition-title--warning": "#FF8F90",
        "color-admonition-title-background--warning": "#002445",
        "color-admonition-title--danger": "#FF8F90",
        "color-admonition-title-background--danger": "#002445",
        "color-admonition-title--attention": "#FF8F90",
        "color-admonition-title-background--attention": "#002445",
        "color-admonition-title--error": "#FF8F90",
        "color-admonition-title-background--error": "#002445",
    },
}

# The PDF takes the colors of the light theme of the HTML: the titles in Brand_2, the code on the
# subtle surface (Blue_1) with the border of the palette, and the titles of the notes in Blue_3 or,
# for the warnings and the errors, in the color of danger, on the subtle surface
latex_admonitions_info = ['note', 'hint', 'tip', 'seealso', 'todo', 'important', 'topic', 'contents', 'sidebar']
latex_admonitions_danger = ['caution', 'warning', 'attention', 'danger', 'error']

latex_sphinxsetup = [
  'InnerLinkColor={HTML}{025A9F}',
  'OuterLinkColor={HTML}{025A9F}',
  'TitleColor={HTML}{002445}',
  'VerbatimColor={HTML}{ECF5FE}',
  'VerbatimBorderColor={HTML}{A5ACB6}',
  'iconpackage=fontawesome7',
]

for admonition_type, color in [(t, '0978CF') for t in latex_admonitions_info] + [(t, 'E30310') for t in latex_admonitions_danger]:
  latex_sphinxsetup.append(f'div.{admonition_type}_title-foreground-TeXcolor={{HTML}}{{{color}}}')
  latex_sphinxsetup.append(f'div.{admonition_type}_title-background-TeXcolor={{HTML}}{{ECF5FE}}')

latex_elements = {
  'preamble': r'\pdfmapfile{+"../../texmf/fonts/map/dvips/fontawesome7/fontawesome7.map"}',
  'sphinxsetup': ', '.join(latex_sphinxsetup),
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
