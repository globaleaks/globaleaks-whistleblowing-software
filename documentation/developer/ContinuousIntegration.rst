======================
Continuous integration
======================
The GlobaLeaks codebase is continuously tested for bug within a complete continuous integration lifecycle implemented.

Testes are performed at every commit by:

* performing continous integration testing with `GitHub Actions <https://github.com/globaleaks/globaleaks-whistleblowing-software/actions>`_;
* tracking tests coverage and code quality with `Codacy <https://app.codacy.com/manual/GlobaLeaks/GlobaLeaks>`_.

Unit tests
==========
Unit tests are implemented by means of python-twisted and trial

Tests can be run manually by issuing:

.. code:: sh

  cd GlobaLeaks/backend
  trial globaleaks

E2E tests
=========
End to end tests are implemented by means of Cypress.

Tests can be run manually by issuing:

.. code:: sh

  cd GlobaLeaks/client
  ./node_modules/cypress/bin/cypress run
