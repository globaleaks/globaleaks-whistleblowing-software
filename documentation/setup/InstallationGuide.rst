Installation Guide
==================
The following guide will help you through the installation of GlobaLeaks.

Before starting the installation, ensure that your system meets the :doc:`Requirements </gettingstarted/Requirements>`.

.. WARNING::
  GlobaLeaks is designed to provide optimal technical anonymity for whistleblowers.
  Additionally, the software can be configured to protect the identity of the platform administrator and the server's location, but this requires advanced setup procedures not covered in this simplified installation guide.
  By executing the commands below, your IP address and system location could be tracked by network providers, and our systems will receive the same information to facilitate software provisioning.

**Install GlobaLeaks**

To install GlobaLeaks, run the following commands:

.. code:: sh

  wget https://deb.globaleaks.org/install-globaleaks.sh
  chmod +x install-globaleaks.sh
  ./install-globaleaks.sh

You may also install GlobaLeaks using Docker. Check out the `docker` directory in our GitHub repository for instructions.

After installation, follow the instructions provided to guide you through accessing the :doc:`Platform wizard </setup/PlatformWizard>`.
