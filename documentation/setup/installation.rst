Installation
============
.. WARNING::
   GlobaLeaks is designed to provide optimal technical anonymity for whistleblowers.
   Protecting the identity of platform administrators and the server's location requires advanced configuration, not covered by this basic guide.

Before You Begin
----------------
Ensure your system meets the required :doc:`Requirements </technical/requirements>`.

Standard Installation
---------------------
Run these commands to download and install GlobaLeaks:

.. code:: bash

   wget https://deb.globaleaks.org/install.sh
   chmod +x install.sh
   ./install.sh

Docker Installation
-------------------
If you prefer Docker, deploy GlobaLeaks with:

.. code:: bash

   docker run -d --name globaleaks \
     -p 80:80 -p 443:443 \
     -v globaleaks-data:/var/globaleaks \
     globaleaks/globaleaks:latest

Post-Installation Steps
-----------------------
After installation:
- Follow the on-screen instructions to complete configuration.
- Access the GlobaLeaks admin interface via your web browser (URL will be shown after setup).
- Refer to the documentation for advanced configuration tips if further anonymity or customization is needed.

Troubleshooting
---------------
If you encounter issues, visit the :doc:`Trouble-Shooting Guide </setup/trouble-shooting>` or check the community forums for help.

