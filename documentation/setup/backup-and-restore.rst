Backup and restore
==================
The data of the application is contained in the directory `/var/globaleaks`.

The backup archive contains the full application data, including reports, attachments, encryption material and configuration secrets. For this reason it must be created and kept in a private directory and never in a shared directory like `/tmp`.

To perform a backup, run the following commands:

.. code:: sh

  mkdir -p /root/backups
  cd /root/backups
  gl-admin backup

After running the command, you will find a `tar.gz` archive in the current directory. The file will be named in the format: `globaleaks_backup_YY_MM_DD.tar.gz`. Alternatively, the output path can be specified as an argument:

.. code:: sh

  gl-admin backup /root/backups/backup-file.tar.gz

When handling backup archives, it is recommended to:

- verify that the archive is readable only by its owner (`chmod 600`);
- encrypt the archive before copying it to any other system or storage;
- preserve the restrictive permissions on every copy;
- delete copies that are no longer needed according to your retention policy.

To perform a restore from an existing backup, run the following command:

.. code:: sh

  gl-admin restore backup-file.tar.gz
