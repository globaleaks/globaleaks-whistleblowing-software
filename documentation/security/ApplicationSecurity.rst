====================
Application security
====================
The GlobaLeaks software aims to adhere to industry-standard best practices, with its security being the result of applied research.

This document details every aspect implemented by the application in relation to security design.

Architecture
============
The software comprises two main components: a `Backend` and a `Client`:

* The Backend is a Python-based server that runs on a physical server and exposes a `REST API <https://en.wikipedia.org/wiki/Representational_state_transfer>`_.
* The Client is a JavaScript client-side web application that interacts with the Backend only through `XHR <https://en.wikipedia.org/wiki/XMLHttpRequest>`_.

Anonymity
=========
Users' anonymity is protected by means of `Tor <https://www.torproject.org>`_ technology.

The application is designed to avoid logging sensitive metadata that could lead to the identification of whistleblowers.

Authentication
==============
The confidentiality of authentication is protected either by `Tor Onion Services v3 <https://www.torproject.org/docs/onion-services.html.en>`_ or `TLS version 1.2+ <https://en.wikipedia.org/wiki/Transport_Layer_Security>`_.

This section describes the authentication methods implemented by the system.

Password
--------
By accessing the login web interface, `Administrators` and `Recipients` need to enter their respective `Username` and `Password`. If the submitted password is valid, the system grants access to the functionality available to that user.

Receipt
-------
`Whistleblowers` access their `Reports` using an anonymous `Receipt`, which is a randomly generated 16-digit sequence created by the Backend when the Report is first submitted. This format resembles a standard phone number, making it easier for whistleblowers to conceal their receipts.

Password security
=================
The system implements the following password security measures:

Password storage
----------------
Passwords are never stored in plaintext; instead, the system maintains only a hashed version. This applies to all authentication secrets, including whistleblower receipts.

The platform stores users’ passwords hashed with a random 128-bit salt, unique for each user.

Passwords are hashed using `Argon2 <https://en.wikipedia.org/wiki/Argon2>`_, a key derivation function selected as the winner of the `Password Hashing Competition <https://en.wikipedia.org/wiki/Password_Hashing_Competition>`_ in July 2015.

The hash involves a per-user salt for each user and a per-system salt for whistleblowers.

Password complexity
-------------------
The system enforces complex passwords by implementing a custom algorithm necessary to ensure reasonable entropy for each authentication secret.

Passwords are scored at three levels: `Strong`, `Acceptable`, and `Insecure`.

* Strong: A strong password should include capital letters, lowercase letters, numbers, and symbols, be at least 12 characters long, and contain a variety of at least 10 different characters.
* Acceptable: An acceptable password should include at least 3 different types of characters from capital letters, lowercase letters, numbers, and symbols, be at least 10 characters long, and contain a variety of at least 7 different characters.
* Insecure: Passwords ranked below the strong or acceptable levels are marked as insecure and are not accepted by the system.

We encourage each end user to use `KeePassXC <https://keepassxc.org>`_ to generate and retain strong, unique passphrases.

Two-factor authentication
-------------------------
The system implements Two-Factor Authentication (2FA) based on `TOTP` using the `RFC 6238 <https://tools.ietf.org/rfc/rfc6238.txt>`_ algorithm and 160-bit secrets.

Users can enroll in 2FA via their own preferences, and administrators can optionally enforce this requirement.

We recommend using `FreeOTP <https://freeotp.github.io/>`_, available `for Android <https://play.google.com/store/apps/details?id=org.fedorahosted.freeotp>`_ and `for iOS <https://apps.apple.com/us/app/freeotp-authenticator/id872559395>`_.

Slowdown on failed login attempts
---------------------------------
The system identifies multiple failed login attempts and implements a slowdown procedure, requiring an authenticating client to wait up to 42 seconds to complete an authentication.

This feature is intended to slow down potential attacks, requiring more resources in terms of time, computation, and memory.

Password change on first login
------------------------------
The system enforces users to change their password at their first login.

Administrators can also enforce a password change for users at their next login.

Periodic password change
------------------------
By default, the system enforces users to change their password at least every year.

This period is configurable by administrators.

Password recovery
-----------------
In case of a lost password, users can request a password reset via the web login interface by clicking on a `Forgot password?` button present on the login page.

When this button is clicked, users are invited to enter their username or email. If the provided username or email corresponds to an existing user, the system will send a reset link to the configured email.

By clicking the link received by email, the user is then invited to set a new password different from the previous one.

If encryption is enabled on the system, a user clicking on the reset link must first enter their `Account Recovery Key`. Only after correct entry will the user be able to set a new password.

Web application security
========================
This section describes the Web Application Security implemented by the software in adherence to the `OWASP Security Guidelines <https://www.owasp.org>`_.

Session management
------------------
The session implementation follows the `OWASP Session Management Cheat Sheet <https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html>`_ security guidelines.

The system assigns a session to each authenticated user. The Session ID is a 256-bit long secret generated randomly by the backend. Each session expires according to a timeout of 30 minutes. Session IDs are exchanged between the client and the backend via a header (`X-Session`) and expire as soon as users close their browser or the tab running GlobaLeaks. Users can explicitly log out via a logout button or implicitly by closing the browser.

Session encryption
------------------
To minimize the exposure of users' encryption keys, the keys are stored in an encrypted format and decrypted only upon each client request.

The implementation uses Libsodium's SecretBox, where the client's session key is used as the secret. Only the client maintains a copy of the session key, while the server retains only a SHA-256 hash.

Cookies and xsrf prevention
---------------------------
Cookies are not used intentionally to minimize XSRF attacks and any possible attacks based on them. Instead of using cookies, authentication is based on a custom HTTP Session Header sent by the client on authenticated requests.

HTTP headers
------------
The system implements a large set of HTTP headers specifically configured to improve software security and achieves a `score A+ by Security Headers <https://securityheaders.com/?q=https%3A%2F%2Ftry.globaleaks.org&followRedirects=on>`_ and a `score A+ by Mozilla Observatory <https://observatory.mozilla.org/analyze/try.globaleaks.org>`_.

Strict-Transport-Security
+++++++++++++++++++++++++
The system implements strict transport security by default.
::

  Strict-Transport-Security: max-age=31536000; includeSubDomains; preload

The default configuration of the application sees this feature disabled.

Content-Security-Policy
+++++++++++++++++++++++
The backend implements a strict `Content Security Policy (CSP) <https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP>`_ preventing any interaction with third-party resources and restricting execution of code by means of `Trusted Types <https://www.w3.org/TR/trusted-types/>`_.
::

  Content-Security-Policy: base-uri 'none'; connect-src 'self'; default-src 'none'; font-src 'self'; form-action 'none'; frame-ancestors 'none'; frame-src 'self'; img-src 'self'; media-src 'self'; script-src 'self' 'report-sample'; style-src 'self' 'report-sample'; trusted-types angular angular#bundler default dompurify; require-trusted-types-for 'script'; report-uri /api/report;

Specific policies are implemented in adherence to the principle of least privilege.

For example:

* The `index.html` source of the app is the only resource allowed to load scripts from the same origin;
* Every dynamic content is strictly sandboxed on a null origin;
* Every untrusted user input or third-party library is executed in a sandbox, limiting its interaction with other application components.

The application implements a dedicated API handler /api/report to receive and log samples of attempts of violations of the content security policy.

Cross-Origin-Embedder-Policy
++++++++++++++++++++++++++++
The backend implements the following `Cross-Origin-Embedder-Policy (COEP) <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cross-Origin-Embedder-Policy>`_:
::

  Cross-Origin-Embedder-Policy: require-corp

Cross-Origin-Opener-Policy
++++++++++++++++++++++++++
The backend implements the following `Cross-Origin-Opener-Policy (COOP) <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cross-Origin-Opener-Policy>`_:
::

  Cross-Origin-Opener-Policy: same-origin

Cross-Origin-Resource-Policy
++++++++++++++++++++++++++++
The backend implements the following `Cross-Origin-Resource-Policy (CORP) <https://developer.mozilla.org/en-US/docs/Web/HTTP/Cross-Origin_Resource_Policy>`_:
::

  Cross-Origin-Resource-Policy: same-origin

Permissions-Policy
++++++++++++++++++
The backend implements the following Permissions-Policy header configuration to limit the possible de-anonymization of the user by disabling dangerous browser features:
::

  Permissions-Policy: camera=() display-capture=() document-domain=() fullscreen=() geolocation=() microphone=() serial=() usb=() web-share=()

X-Frame-Options
+++++++++++++++
In addition to implementing Content Security Policy level 3 to prevent the application from being included in an iframe, the backend also implements the outdated X-Frame-Options header to ensure that iframes are always prevented in any circumstance, including on outdated browsers:
::

  X-Frame-Options: deny

Referrer-Policy
+++++++++++++++
Web browsers usually attach referrers in their HTTP headers as they browse links. The platform enforces a referrer policy to avoid this behavior.
::

  Referrer-Policy: no-referrer

X-Content-Type-Options
++++++++++++++++++++++
To avoid automatic MIME type detection by the browser when setting the Content-Type for specific output, the following header is used:
::

  X-Content-Type-Options: nosniff

Cache-Control
+++++++++++++
To prevent or limit forensic traces left on devices used by whistleblowers and in devices involved in communication with the platform, as specified in section ``3. Storing Responses in Caches`` of `RFC 7234 <https://tools.ietf.org/html/rfc7234>`__, the platform uses the ``Cache-Control`` HTTP header with the configuration ``no-store`` to instruct clients and possible network proxies to disable any form of data caching.
::

  Cache-Control: no-store

Crawlers policy
---------------
For security reasons, the backend instructs crawlers to avoid caching and indexing of the application and uses the ``robots.txt`` file to allow crawling only of the home page. Indexing the home page is considered best practice to promote the platform's existence and facilitate access for potential whistleblowers.

The implemented configuration is as follows:
::

  User-agent: *
  Allow: /$
  Disallow: *

The platform also instructs crawlers to avoid caching by injecting the following HTTP header:
::

  X-Robots-Tag: noarchive

For highly sensitive projects where the platform is intended to remain ``hidden`` and communicated to potential whistleblowers directly, it can be configured to disable indexing completely.

In such cases, the following HTTP header is used:
::

  X-Robots-Tag: noindex

Anchor tags and external urls
-----------------------------
The client opens external URLs in a new tab, independent of the application context, by setting ``target='_blank'``` on remote or untrusted anchor tag.
::

  <a href="url" target="_blank">link title</a>

Input validation
----------------
The application implements strict input validation both on the backend and on the client.

On the backend
++++++++++++++
Each client request is strictly validated by the backend against a set of regular expressions, and only requests matching the expressions are processed.

Additionally, a set of rules is applied to each request type to limit potential attacks. For example, any request is limited to a payload of 1MB.

On the client
+++++++++++++
Each server output is strictly validated by the client at rendering time using the Angular component `ngSanitize.$sanitize <http://docs.angularjs.org/api/ngSanitize.$sanitize>`_.

Few configurations accepts Markdown input and every input is strictly validated stripping every HTML tag with `DOMPurify <https://github.com/cure53/DOMPurify>`_

Form autocomplete off
---------------------
Forms implemented by the platform use the HTML5 form attribute to instruct the browser not to cache user data for form prediction and autocomplete on subsequent submissions.

This is achieved by setting `autocomplete="off" <https://www.w3.org/TR/html5/forms.html=autofilling-form-controls:-the-autocomplete-attribute>`__ on the relevant forms or attributes.

Network security
================
Connection anonymity
--------------------
User anonymity is provided through the implementation of `Tor <https://www.torproject.org/>`__ technology. The application implements an ``Onion Service v3`` and advises users to use the Tor Browser when accessing it.

Connection encryption
---------------------
User connections are always encrypted, either through the `Tor Protocol <https://www.torproject.org>`__ when using the Tor Browser or via `TLS <https://en.wikipedia.org/wiki/Transport_Layer_Security>`__ when accessed through a common browser.

Using ``Tor`` is recommended over HTTPS due to its advanced resistance to selective interception and censorship, making it difficult for a third party to capture or block access to the site for specific whistleblowers or departments.

The software also facilitates easy setup of ``HTTPS``, offering both automatic setup via `Let's Encrypt <https://letsencrypt.org/>`__ and manual configuration.

TLS certificates are generated using `NIST Curve P-384 <https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf>`__.

The configuration enables only ``TLS1.2+`` and is fine-tuned and hardened to achieve `SSLLabs grade A+ <https://www.ssllabs.com/ssltest/analyze.html?d=try.globaleaks.org>`__.

In particular, only the following ciphers are enabled:
::

  TLS13-AES-256-GCM-SHA384
  TLS13-CHACHA20-POLY1305-SHA256
  TLS13-AES-128-GCM-SHA256
  ECDHE-ECDSA-AES256-GCM-SHA384
  ECDHE-RSA-AES256-GCM-SHA384
  ECDHE-ECDSA-CHACHA20-POLY1305
  ECDHE-RSA-CHACHA20-POLY1305
  ECDHE-ECDSA-AES128-GCM-SHA256
  ECDHE-RSA-AES128-GCM-SHA256

Network sandboxing
-------------------
The GlobaLeaks backend integrates `iptables <https://www.netfilter.org/>`__ by default and implements strict firewall rules that restrict incoming network connections to HTTP and HTTPS on ports 80 and 443.

Additionally, the application allows anonymizing outgoing connections, which can be configured to route through Tor.

Data encryption
===============
Submission data, file attachments, messages, and metadata exchanged between whistleblowers and recipients are encrypted using the GlobaLeaks :doc:`EncryptionProtocol`.

GlobaLeaks also incorporates various other encryption components. The main libraries and their uses are:

* `Python-NaCL <https://github.com/pyca/pynacl>`__: used for implementing data encryption
* `PyOpenSSL <https://github.com/pyca/pyopenssl>`__: used for implementing HTTPS
* `Python-Cryptography <https://cryptography.io>`__: used for implementing authentication
* `Python-GnuPG <http://pythonhosted.org/python-gnupg/index.html>`__: used for encrypting email notifications and file downloads via ```PGP```

Application sandboxing
======================
The GlobaLeaks backend integrates `AppArmor <https://apparmor.net/>`__ by default and implements a strict sandboxing profile, allowing the application to access only the strictly required files. Additionally, the application runs under a dedicated user and group "globaleaks" with reduced privileges.

Database security
=================
The GlobaLeaks backend uses a hardened local SQLite database accessed via SQLAlchemy ORM.

This design choice ensures the application can fully control its configuration while implementing extensive security measures in adherence to the `security recommendations by SQLite <https://sqlite.org/security.html>`__.

Secure deletion
---------------
The GlobaLeaks backend enables SQLite’s secure deletion capability, which automatically overwrites the database data upon each delete query:
::

  PRAGMA secure_delete = ON

Auto vacuum
-----------
The platform enables SQLite’s auto vacuum capability for automatic cleanup of deleted entries and recall of unused pages:
::

  PRAGMA auto_vacuum = FULL

Limited database trust
----------------------
The GlobaLeaks backend uses the SQLite `trusted_schema <https://www.sqlite.org/src/doc/latest/doc/trusted-schema.md>`__ pragma to limit trust in the database, mitigating risks of malicious corruption.
::

  PRAGMA trusted_schema = OFF

Limited database functionalities
--------------------------------
The GlobaLeaks backend restricts SQLite functionalities to only those necessary for running the application, reducing the potential for exploitation in case of SQL injection attacks.

This is implemented using the ```conn.set_authorizer``` API and a strict authorizer callback that authorizes only a limited set of SQL instructions:
::

  SQLITE_FUNCTION: count, lower, min, max
  SQLITE_INSERT
  SQLITE_READ
  SQLITE_SELECT
  SQLITE_TRANSACTION
  SQLITE_UPDATE

DoS resiliency
==============
To mitigate denial of service attacks, GlobaLeaks applies the following measures:

* Implements a proof-of-work (hashcash) on each unauthenticated request to limit automation.
* Applies rate limiting on authenticated sessions.
* Limits the possibility of triggering CPU-intensive routines by external users (e.g., limits on query and job execution times).
* Monitors activity to detect and respond to attacks, implementing proactive security measures to prevent DoS (e.g., slowing down fast operations).

Proof of work on users' sessions
--------------------------------
The system implements an automatic `Proof of Work <https://en.wikipedia.org/wiki/Proof_of_work>`__ based on the hashcash algorithm for every user session, requiring clients to request a token and continuously solve a computational problem to acquire and renew the session.

Rate limit on users' sessions
------------------------------
The system implements rate limiting on user sessions, preventing more than 5 requests per second and applying increasing delays on requests that exceed this threshold.

Rate limit on whistleblowers' reports and attachments
-----------------------------------------------------
The system applies rate limiting on whistleblower reports and attachments, preventing new submissions and file uploads if thresholds are exceeded.

Implemented thresholds are:

.. csv-table::
   :header: "Threshold Variable", "Goal", "Default Threshold Setting"

   "threshold_reports_per_hour", "Limit the number of reports that can be filed per hour", "20"
   "threshold_reports_per_hour_per_ip", "Limit the number of reports that can be filed per hour by the same IP address", "5"
   "threshold_attachments_per_hour_per_ip", "Limit the number of attachments that can be uploaded per hour by the same IP address", "120"
   "threshold_attachments_per_hour_per_report", "Limit the number of attachments that can be uploaded per hour on a report", "30"

In case of necessity, threshold configurations can be adjusted using the `gl-admin` command as follows:
::

  gl-admin setvar threshold_reports_per_hour 1

Other measures
==============
Browser history and forensic traces
-----------------------------------
The entire application is designed to minimize or reduce the forensic traces left by whistleblowers on their devices while filing reports.

When accessed via the Tor Browser, the browser ensures that no persistent traces are left on the user's device.

To prevent or limit forensic traces in the browser history of users accessing the platform via a common browser, the application avoids changing the URI during whistleblower navigation. This prevents the browser from logging user activities and offers high plausible deniability, making the whistleblower appear as a simple visitor to the homepage and avoiding evidence of any submission.

Secure file management
----------------------
Secure file download
++++++++++++++++++++
Any attachment uploaded by anonymous whistleblowers might contain malware, either intentionally or not. It is highly recommended, if possible, to download files and access them on an air-gapped machine disconnected from the network and other sensitive devices. To facilitate safe file downloads and transfers using a USB stick, the application provides the option to export reports, enabling the download of a ZIP archive containing all report content. This reduces the risk of executing files during the transfer process.

Safe file opening
+++++++++++++++++
For scenarios where the whistleblower's trustworthiness has been validated or in projects with a low-risk threat model, the application offers an integrated file viewer. This viewer, leveraging modern browser sandboxing capabilities, allows the safe opening of a limited set of file types considered more secure than accessing files directly through the operating system. This feature is disabled by default. Administrators should enable it only after thorough evaluation and ensure that recipients' browsers are kept up-to-date.

The supported file formats are:

* AUDIO
* CSV
* IMAGE
* PDF
* VIDEO
* TXT

The default configuration has this feature disabled.

PGP encryption
++++++++++++++
The system offers an optional PGP encryption feature.

When enabled, users can activate a personal PGP key that will be used by the system to encrypt email notifications and files on-the-fly.

This feature is recommended for high-risk threat models, especially when used in conjunction with air-gapped systems for report visualization.

The default configuration has this feature disabled.

Encryption of temporary files
-----------------------------
Files uploaded and temporarily stored on disk during the upload process are encrypted with a ChaCha20 and temporary 256bit keys to prevent any unencrypted data from being written to disks. Key files are stored in memory and are unique for each file being uploaded.

Secure file delete
------------------
Every file deleted by the application is overwritten before the file space is released on disk.

The overwrite routine is executed by a periodic scheduler and follows these steps:

* A first overwrite writes 0 across the entire file;
* A second overwrite writes 1 across the entire file;
* A third overwrite writes random bytes across the entire file.

Exception logging and redaction
-------------------------------
To quickly diagnose potential software issues when client exceptions occur, they are automatically reported to the backend. The backend temporarily caches these exceptions and sends them to the backend administrator via email.

To prevent inadvertent information leaks, logs are processed through filters that redact email addresses and UUIDs.

Entropy sources
---------------
The primary source of entropy for the platform is `/dev/urandom`.

UUIDv4 randomness
-----------------
System resources like submissions and files are identified by UUIDv4 to make them unguessable by external users and limit potential attacks.

TLS for smtp notification
-------------------------
All notifications are sent through an SMTP channel encrypted with TLS, using either SMTP/TLS or SMTPS, depending on the configuration.
