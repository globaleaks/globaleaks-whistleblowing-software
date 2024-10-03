=======================
Development Environment
=======================
This guide describes how to set up an environment in order to contribute to the development of GlobaLeaks.

Requirements
============
The guide assumes you run a Debian based system and that the following software is installed on your system:

* debhelper
* devscripts
* dh-apparmor
* dh-python
* git
* grunt-cli
* node
* npm
* python3
* python3-dev
* python3-pip
* python3-setuptools
* python3-sphinx
* python3-virtualenv

Setup
=====
The repository could be cloned with:

.. code:: sh

  git clone https://github.com/globaleaks/whistleblowing-software.git

Client dependencies could be installed by issuing:

.. code:: sh

  cd GlobaLeaks/client
  npm install -d
  grunt copy:sources

Backend dependencies could be installed by issuing:

.. code:: sh

  cd GlobaLeaks/backend
  python3 -mvenv env
  source env/bin/activate
  pip3 install -r requirements.txt

This will create for you a python virtualenv in the directory env containing all the required python dependencies. To leave the virtualenv, type ``deactivate``.

Then, anytime you will want to activate the environment to run globaleaks you will just need to issue the command:

.. code:: sh

  cd GlobaLeaks/backend && source ./env/bin/activate

Setup the client:

.. code:: sh

  cd GlobaLeaks/client
  npm install -d
  grunt build

Setup the backend and its dependencies:

.. code:: sh

  cd GlobaLeaks/backend
  python3 -m venv env
  source env/bin/activate
  pip3 install -r requirements.txt

Run
===
To run globaleaks from sources within the development environment you should issue:

.. code:: sh

  cd GlobaLeaks/backend
  source env/bin/activate
  bin/globaleaks -z -n

GlobaLeaks will start and be reachable at the following address https://127.0.0.1:8443

Building The Docs
=================
To build the documentation:

.. code:: sh

  cd GlobaLeaks/documentation
  pip install -r requirements.txt
  make html

To edit the docs with hot-reload functionality:

.. code:: sh

  cd GlobaLeaks/documentation
  python3 -m venv env
  source env/bin/activate
  pip install -r requirements.txt
  make dev

Sphinx server will start and be reachable at the following address http://127.0.0.1:8000 in the web browser.
