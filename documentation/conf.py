# -*- coding: utf-8 -*-
#
# GlobaLeaks documentation build configuration file, created by
# sphinx-quickstart on Thu Jul  6 16:34:48 2017.
#
import gettext
import os
import sys

sys.path.insert(0, os.path.abspath('../backend'))

from globaleaks import __author__,  __copyright__, __version__

autodoc_member_order = 'bysource'
autodoc_default_flags = ['members', 'show-inheritance', 'undoc-members']

extensions = [
  'sphinx_rtd_theme',
  'sphinx_copybutton',
  'sphinx_sitemap'
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
locale_dirs = ['locale/']
locale_dir = os.path.join(os.path.dirname(__file__), locale_dirs[0])
gettext.bindtextdomain('sphinx', locale_dir)
gettext.textdomain('sphinx')
gettext_compact = 'sphinx'

exclude_patterns = ['_build']
show_authors = False
pygments_style = 'sphinx'

html_theme = 'sphinx_rtd_theme'
html_logo = 'logo-html.png'
html_baseurl = 'https://docs.globaleaks.org/'
html_favicon = '../client/app/assets/data/favicon.ico'
html_show_copyright = False
htmlhelp_basename = 'globaleaks'
html_static_path = ['_static']

html_context = {
'description': 'GlobaLeaks is free, open souce whistleblowing software enabling anyone to easily set up and maintain a secure reporting platforms',
'keywords': 'globaleaks, whistleblowing, globaleaks-whistleblowing-software',
'author': 'GLOBALEAKS',
}

latex_elements = {
  'sphinxsetup': 'TitleColor={HTML}{3679BB}, \
  InnerLinkColor={HTML}{3679BB}, \
  OuterLinkColor={HTML}{3679BB}',
}

latex_documents = []

latex_logo = 'logo-latex.pdf'

man_pages = [
(master_doc, 'globaleaks', u'Documentation',
 [author], 1)
]

texinfo_documents = [
(master_doc, 'GLOBALEAKS', u'Documentation',
 author, 'GLOBALEAKS', ' GlobaLeaks is free, open source whistleblowing software enabling anyone to easily set up and maintain a secure reporting platforms',
 'Miscellaneous'),
]

html_theme_options = {
  'style_nav_header_background': '#3679BB',
}

def setup(app):
    translation = gettext.translation('sphinx', localedir=locale_dir, languages=[app.config.language], fallback=True)
    document_title = translation.gettext('Documentation')
    app.config.latex_documents = [(master_doc, 'GlobaLeaks.tex', document_title, '', 'manual'),]

    app.add_css_file("custom.css")
    app.add_js_file("custom.js")
