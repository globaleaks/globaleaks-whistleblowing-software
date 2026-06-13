Installation
============
.. WARNING::
  GlobaLeaks is designed to provide optimal technical anonymity for whistleblowers.
  Additionally, the software can be configured to protect the identity of the platform administrator and the server's location, but this requires advanced setup procedures not covered in this simplified installation guide.

Before you begin, make sure your system meets the :doc:`Requirements </technical/requirements>`.

To install, run the following commands:

.. code:: sh

  wget https://deb.globaleaks.org/install.sh
  echo "0000000000000000000000000000000000000000000000000000000000000000  install.sh" | sha256sum -c
  chmod +x install.sh
  ./install.sh

The ``sha256sum -c`` step verifies the integrity of the downloaded script
against the checksum published in this guide before running it as root.
It prints ``install.sh: OK`` on success and fails otherwise.

To install using Docker, run the following commands:

.. code:: sh

  docker run -d --name globaleaks \
    --platform linux/amd64 \
    -p 80:8080 \
    -p 443:8443 \
    -v globaleaks-data:/var/globaleaks \
    globaleaks/globaleaks:latest

After installation, follow the on-screen instructions to access and configure your platform.
