Backup and restore
==================
The data of the application is contained in the directory `/var/globaleaks`.

.. warning::

  A backup stores the data encrypted exactly as it was at the time the backup was
  taken. Because each account's data is protected by keys derived from that
  account's password, a backup can be decrypted only with the passwords that were
  in effect when the backup was created. If a user later changes or resets their
  password, older backups remain accessible only with the corresponding older
  password. Keep a secure record of previous passwords if you need to retain
  access to older backups.

.. note::

  This limitation does not apply when key escrow is enabled. With escrow, each
  account's keys are additionally protected with the platform escrow key held by
  the administrators, so an administrator who retains access to it through their
  account recovery key can recover the data in any backup regardless of later
  password changes. When key escrow is enabled and administrator recovery keys
  are properly maintained, keeping a record of previous passwords is therefore
  not necessary.

Automatic backups
-----------------
GlobaLeaks can take periodic, self-contained snapshots of its data without
stopping the service. Automatic backups are disabled by default and can be
enabled and tuned from the administration interface, where you can configure:

- the time of day at which backups run;
- the period between two backups (in hours);
- the number of snapshots to retain (older snapshots are pruned automatically).

Snapshots are written under `/var/globaleaks/backups`:

- `/var/globaleaks/backups/snapshots/<timestamp>/` holds each published snapshot,
  a full and independent copy of the application data (database and files);
- `/var/globaleaks/backups/tmp/` is a local staging area used while a snapshot is
  being built.

To save disk space, unchanged files are hardlinked across snapshots, so every
snapshot is a complete tree on disk while only the changed files cost additional
space.

Storing snapshots on remote or external storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To keep snapshots off the local disk (NFS, CIFS, sshfs, or another volume), mount
the remote storage on `/var/globaleaks/backups/snapshots` only, leaving
`/var/globaleaks/backups/tmp` on the local disk. The mount point must be writable
by the `globaleaks` user.

Mounting the archive directory while keeping the staging directory local is
important: the database snapshot is first taken on the local disk and only then
copied into the archive, so the database is never written page by page over the
network and write operations on the running application are not blocked during
the transfer. Do not mount the whole `/var/globaleaks/backups` directory.

The AppArmor profile confines the backend to `/var/globaleaks/**`, so it already
covers anything mounted under it and no profile change is required.

Mount the storage only after the installation has completed: the
`/var/globaleaks` directory and the `globaleaks` user are created by the package
post-install step, and pre-creating the directory to prepare a mount point in
advance skips the ownership and permission setup.

Restoring from a snapshot
~~~~~~~~~~~~~~~~~~~~~~~~~~~
A snapshot is a plain copy of the application data, so a restore is a file copy
performed while the service is stopped:

.. code:: sh

  systemctl stop globaleaks
  rsync -a --delete --exclude='backups' /var/globaleaks/backups/snapshots/<timestamp>/ /var/globaleaks/
  chown -R globaleaks:globaleaks /var/globaleaks
  systemctl start globaleaks

Replace `<timestamp>` with the snapshot you want to restore.

Manual backups
--------------
To perform a manual backup, run the following command:

.. code:: sh

  gl-admin backup

After running the command, you will find a `tar.gz` archive in `/tmp`. The file will be named in the format: `globaleaks_backup_YY_MM_DD.tar.gz`.


To perform a restore from an existing backup, run the following command:

.. code:: sh

  gl-admin restore backup-file.tar.gz
