Backup and restore
==================

To perform a manual backup, you can use the following bash script:

.. code::

   #!/bin/sh
   set -e

   if [ -d "/var/globaleaks" ]; then
     timestamp=$(date +%s)
     version=$(dpkg -s globaleaks | grep '^Version:' | cut -d ' ' -f2)
     filepath="/var/globaleaks/backups/globaleaks-$version-$timestamp.tar.gz"
     echo "Creating backup of /var/globaleaks in $filepath"
     mkdir -p /var/globaleaks/backups
     chown globaleaks:globaleaks /var/globaleaks/backups
     tar --exclude='/var/globaleaks/backups' -zcvf "$filepath" /var/globaleaks
   fi

After running the script, you will find a `tar.gz` archive in `/var/globaleaks/backups`. The file will be named in the format: `globaleaks-$version-$timestamp.tar.gz`.

GlobaLeaks automatically performs a backup during each platform update. These backups are retained under a data retention policy and are deleted 15 days after the update.

To restore an existing backup:

- Ensure that GlobaLeaks is not running; you can stop it using: `service globaleaks stop`.
- Identify the version of GlobaLeaks required for the restoration, which is indicated in the backup filename.
- Extract the contents of the archive to `/var/globaleaks` using: `tar -zxvf backup.tar.gz`.
- Install the required version of GlobaLeaks with: `apt-get install globaleaks=<version>` (e.g., `globaleaks=3`).
