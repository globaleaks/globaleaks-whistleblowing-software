Troubleshooting
===============

Issues and bug reporting
------------------------

If you encounter any issues and are unable to run GlobaLeaks:

- Ensure you strictly follow the Installation Guide.
- Verify that you meet the Technical Requirements for hardware and operating system version.
- Search the support forum to see if a user has already encountered your issue: `GlobaLeaks Discussions <https://github.com/orgs/globaleaks/discussions>`_
- Report the issue on the official software issue tracker: `GlobaLeaks Issues <https://github.com/globaleaks/globaleaks-whistleblowing-software/issues>`_

Useful debugging commands
-------------------------

Depending on your setup, here are some common checks to determine if GlobaLeaks is working:

- Is the service running?

::

  service globaleaks status

- Is the service responding on the loopback interface?

::

  curl -kis -vvv localhost:8433

- Is the service listening on external interfaces?

::

  netstat -tap

- Are exceptions being generated?

::

  less /var/globleaks/log/globaleaks.log


Log files
---------
Here are some useful logs and their corresponding files when GlobaLeaks is installed:

**GlobaLeaks process:**

::

  /var/globaleaks/log/globaleaks.log


The verbosity of the logs is configurable via the web interface of the software under Advanced Settings.
