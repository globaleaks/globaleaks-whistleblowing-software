Backup and restore
==================
The data of the application is contained in the directory `/var/globaleaks`.

To perform a backup, run the following command:

.. code:: sh

  gl-admin backup

After running the command, you will find a `tar.gz` archive in `/tmp`. The file will be named in the format: `globaleaks_backup_YY_MM_DD.tar.gz`.


To perform a restore from an existing backup, run the following command:

.. code:: sh

  gl-admin restore backup-file.tar.gz
