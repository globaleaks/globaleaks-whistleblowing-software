Release procedure
=================
This is the procedure followed to publish a new GlobaLeaks release.

A release is represented by:

* A version bump;
* An updated CHANGELOG;
* A commit titled "Bump to version $number";
* A tag commit $version signed by a core developer with their own key;
* An updated package on deb.globaleaks.org;
* A signed repository.

Release versioning
==================
A new release version is issued by means of the official version bump script by issuing:

.. code:: sh

  cd GlobaLeaks && ./scripts/bump_version.sh $version

Release tagging
===============
The release is tagged by meand of the following commands

.. code:: sh
  export DEBFULLNAME="GlobaLeaks software signing key"
  export DEBEMAIL="info@globaleaks.org"
  git tag -s v0.1 -m 'GlobaLeaks version 0.1'
  git push origin --tags

Release packaging
=================
The package is built by means of the official build script by issuing:

.. code:: sh

  cd GlobaLeaks && ./scripts/build.sh -d all

This command builds a package for each supported distribution and version.

Package publishing
==================
The package is published on https://deb.globaleaks.org by issuing:

.. code:: sh

  dput globaleaks ../globaleaks_${version}_all.changes

Repository signing
==================
The release is then signed by a core developer by using the official project key via:

.. code:: sh

  gpg --detach-sign --digest-algo SHA512 -o Release.gpg Release
