Release Procedure
=================
This is the procedure followed to publish a new GlobaLeaks release.

A release is represented by:

* A version bump;
* An updated CHANGELOG;
* A commit titled "Bump to version $number";
* A tag commit $version signed by a core developer with their own key;
* An updated package on deb.globaleaks.org;
* A signed repository.

Release Tagging
===============
To release is tagger by means of the official version bump script by issuing:

.. code:: sh

  cd GlobaLeaks && ./scripts/bump_version.sh $version

Release Packaging
=================
The package is built by means of the official build script by issuing:

.. code:: sh

  cd GlobaLeaks && ./scripts/build.sh -d all

This command builds a package for each supported distribution and version.

Package Publishing
==================
The package is published on https://deb.globaleaks.org by issuing:

.. code:: sh

  dput globaleaks ../globaleaks_${version}_all.changes

Repository Signing
==================
The release is then signed by a core developer by using the official project key via:

.. code:: sh

  gpg --detach-sign --digest-algo SHA512 -o Release.gpg Release
