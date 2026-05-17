Update
======
Software update
--------------
To safely update a GlobaLeaks installation please proceed with a backup of your setup by following the :doc:`Backup and Restore </setup/backup-and-restore>` guide.

This is necessary so that if something goes wrong and you need to rollback, you will be able to just uninstall the current package, then install the same version of globaleaks that was previously installed and working.

In order to update GlobaLeaks perform the following commands:

.. code::

   apt update && apt install globaleaks

Distribution upgrade
--------------------
For security and stability reasons it is recommended to not perform an automatic distribution upgrade.

GlobaLeaks could be instead easily migrated to a new up-to-date Debian system with the following recommended instructions:

- create an archive backup of /var/globaleaks
- instantiate the latest Debian available
- log on the new server and extract the backup in /var/globaleaks
- follow the :doc:`Installation Guide </setup/installation>`; GlobaLeaks while installing will recognize the presence of an existing data directory and will use it
