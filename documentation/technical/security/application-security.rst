====================
Application security
====================
The GlobaLeaks software aims to adhere to industry-standard best practices, with its security being the result of applied research.

This document details every aspect implemented by the application in relation to security design.

Architecture
============
The software comprises two main components: a `Backend` and a `Client`:

* The Backend is a Python-based server that runs on a physical server and exposes a `REST API <https://en.wikipedia.org/wiki/Representational_state_transfer>`_.
* The Client is a TypeScript client-side web application that interacts with the Backend only through `XHR <https://en.wikipedia.org/wiki/XMLHttpRequest>`_.

Following the `Zero Trust paradigm <https://nvlpubs.nist.gov/nistpubs/specialpublications/NIST.SP.800-207.pdf>`_ and aiming at implementing a fully auditable technology both the Backend and the Client are implemented using only open-source libraries.

Here could be found the Software Bills of Materials: `SBOM <https://github.com/globaleaks/globaleaks-whistleblowing-software/dependency-graph/sbom>`_.

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
Passwords are never stored on the server either in plaintext or in form on hash; instead, the system maintains only the hash of a key derived from the user password.

Passwords are hashed using `Argon2 <https://en.wikipedia.org/wiki/Argon2>`_ with a configuration of 16 iterations and 128MB of RAM, a per-user salt for each user and a per-system salt for whistleblowers.

The hashing algorithm used to compute the key hash is SHA256.

Password complexity
-------------------
The system enforces complex passwords by implementing a custom algorithm necessary to ensure reasonable entropy for each authentication secret.

Passwords are scored at three levels: `Strong`, `Acceptable`, and `Insecure`.

* Strong: A strong password should include capital letters, lowercase letters, numbers, and symbols, be at least 14 characters long, and contain a variety of at least 12 different characters.
* Acceptable: An acceptable password should include capital letters, lowercase letters, numbers, and symbols, be at least 12 characters long, and contain a variety of at least 10 different characters.
* Insecure: Passwords ranked below the strong or acceptable levels are marked as insecure and are not accepted by the system.

We encourage each end user to use `KeePassXC <https://keepassxc.org>`_ to generate and retain strong, unique passphrases.

Two-factor authentication
-------------------------
The system implements Two-Factor Authentication (2FA) based on `TOTP` using the `RFC 6238 <https://tools.ietf.org/rfc/rfc6238.txt>`_ algorithm and 160-bit secrets.

Users can enroll in 2FA via their own preferences, and administrators can optionally enforce this requirement.

We recommend using `FreeOTP <https://freeotp.github.io/>`_, available `for Android <https://play.google.com/store/apps/details?id=org.fedorahosted.freeotp>`_ and `for iOS <https://apps.apple.com/us/app/freeotp-authenticator/id872559395>`_.

Slowdown on failed login attempts
---------------------------------
The system identifies multiple failed login attempts and implements a slowdown procedure, requiring an authenticating client to wait up to 60 seconds to complete an authentication.

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

No cookies
----------
The system does not use cookies or any persistent local storage mechanisms for authentication or session handling.

This design prioritizes user privacy and significantly reduces the risk of Cross-Site Request Forgery (CSRF) attacks by eliminating the use of cookies and the need for additional CSRF tokens.

Session management
------------------
The session implementation follows the `OWASP Session Management Cheat Sheet <https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html>`_ security guidelines.

Each authenticated user is assigned a session identified by a 256-bit cryptographically secure random Session ID, generated by the backend. Session IDs are transmitted between the client and the backend exclusively via a custom HTTP header (X-Session).

Sessions have a fixed inactivity timeout of 30 minutes and are invalidated immediately upon expiration. Users may explicitly terminate their session using the logout function.

Because session data is not stored persistently and exists only for the lifetime of the active browser tab, sessions are implicitly terminated when the user closes the browser or the tab running GlobaLeaks.

Session encryption
------------------
To minimize the exposure of users' encryption keys, the keys are stored in an encrypted format and decrypted only upon each client request.

The implementation uses Libsodium's SecretBox, where the client's session key is used as the secret. Only the client maintains a copy of the session key, while the server retains only a SHA-256 hash.

HTTP headers
------------
The system implements a large set of HTTP headers specifically configured to improve software security and achieves a `score A+ by Security Headers <https://securityheaders.com/?q=https%3A%2F%2Fdemo.globaleaks.org&followRedirects=on>`_ and a `score A+ by Mozilla Observatory <https://observatory.mozilla.org/analyze/demo.globaleaks.org>`_.

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

  Content-Security-Policy: base-uri 'none'; connect-src 'self'; default-src 'none'; font-src 'self'; form-action 'none'; frame-ancestors 'none'; frame-src 'self'; img-src 'self'; media-src 'self'; script-src 'self'; style-src 'self' 'nonce-{random}'; trusted-types angular angular#bundler dompurify default; require-trusted-types-for 'script'; report-to csp-endpoint
  Reporting-Endpoints: csp-endpoint="/api/report"

The ``style-src`` directive is bound to a per-response cryptographic ``nonce``, so that only the stylesheet emitted by the application is allowed to execute, following the standard CSP nonce-based approach.

Specific policies are implemented in adherence to the principle of least privilege.

For example:

* The `index.html` source of the app is the only resource allowed to load scripts that could be loaded only on the same origin;
* Every dynamic content is strictly sandboxed on a null origin;
* Every untrusted user input or third-party library is executed in a sandbox, limiting its interaction with other application components.

The application implements a dedicated API handler /api/report to receive reporting of any attempt of violation of the content security policy.

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

Origin-Agent-Cluster
++++++++++++++++++++
The backend requests origin-keyed agent clustering by means of the `Origin-Agent-Cluster <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Origin-Agent-Cluster>`__ header, so that the application is isolated in its own agent cluster instead of being grouped with other same-site origins. This provides defense in depth against cross-origin information-leak attacks of the Spectre class, complementing the Cross-Origin isolation policies described above:
::

  Origin-Agent-Cluster: ?1

Permissions-Policy
++++++++++++++++++
The backend implements the following Permissions-Policy header configuration to limit the possible de-anonymization of the user by disabling dangerous browser features:
::

  Permissions-Policy: accelerometer=(),ambient-light-sensor=(),bluetooth=(),camera=(),clipboard-read=(),clipboard-write=(),document-domain=(),display-capture=(),fullscreen=(),geolocation=(),gyroscope=(),idle-detection=(),keyboard-map=(),local-fonts=(),magnetometer=(),microphone=(),midi=(),notifications=(),payment=(),push=(),screen-wake-lock=(),serial=(),speaker-selection=(),usb=(),web-share=(),xr-spatial-tracking=()

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

X-Frame-Options
+++++++++++++++
As an additional defense in depth against clickjacking, the backend sets the ``X-Frame-Options`` header to ``deny``. On modern browsers framing is already prevented by the ``frame-ancestors 'none'`` directive of the Content Security Policy, which supersedes this header; ``X-Frame-Options`` is retained only as a redundant safeguard.
::

  X-Frame-Options: deny

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
Each server output is strictly sanitized by the client at rendering time through Angular's built-in security model. The framework automatically applies context-aware sanitization to every value bound into the DOM via interpolation, property bindings, attribute bindings, and the ``[innerHTML]`` directive. Sanitization is performed by Angular's `DomSanitizer <https://angular.dev/api/platform-browser/DomSanitizer>`__ service according to the binding's `SecurityContext
<https://angular.dev/api/core/SecurityContext>`__ (``HTML``, ``STYLE``, ``URL``, ``RESOURCE_URL``, ``SCRIPT``), stripping or escaping any
untrusted construct before it can reach the DOM.

A few configurations additionally accept Markdown input; in those cases every input is strictly validated by stripping any HTML construct using
`DOMPurify <https://github.com/cure53/DOMPurify>`__, registered as a Trusted Types policy so that its output integrates cleanly with the application's CSP.

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

The configuration enables only ``TLS1.2+`` and is fine-tuned and hardened to achieve `SSLLabs grade A+ <https://www.ssllabs.com/ssltest/analyze.html?d=demo.globaleaks.org>`__.

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

In addition, the backend enables SQLite's `defensive mode <https://www.sqlite.org/c3ref/c_dbconfig_defensive.html>`__, which disables interfaces that would otherwise allow ordinary SQL to corrupt or alter the database in surprising ways:
::

  SQLITE_DBCONFIG_DEFENSIVE = ON

To further reduce the attack surface available through SQL, the backend disables double-quoted string literals in both DDL and DML statements, ensuring that any identifier accidentally double-quoted in a query is rejected rather than silently reinterpreted as a string:
::

  PRAGMA dqs_ddl = 0
  PRAGMA dqs_dml = 0

Disabled SQL features
---------------------
The GlobaLeaks backend disables SQLite features that are not used by the application and that could otherwise be abused as execution sinks in case of a SQL injection:
::

  SQLITE_DBCONFIG_ENABLE_TRIGGER = OFF
  SQLITE_DBCONFIG_ENABLE_VIEW    = OFF

Limited database functionalities
--------------------------------
The GlobaLeaks backend restricts SQLite functionalities to only those necessary for running the application, reducing the potential for exploitation in case of SQL injection attacks.

This is implemented using the ```conn.set_authorizer``` API and a strict authorizer callback that authorizes only a limited set of SQL instructions:
::

  SQLITE_DELETE
  SQLITE_FUNCTION: count, length, lower, min, max, substr
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

Specifically the algorithm used to perform the hash is Argon2id with requirement of 1 iteration and 1MB of RAM.

Rate limit on users' sessions
------------------------------
The system implements rate limiting on user sessions, preventing more than 5 requests per second and applying increasing delays on requests that exceed this threshold.

Rate limit on logins, whistleblowers' reports and attachments and operations
----------------------------------------------------------------------------
The system applies rate limiting on whistleblower reports and attachments and any other operation blocking or delaying the request if thresholds are exceeded.

Implemented thresholds are:

.. csv-table::
   :header: "Threshold Variable", "Goal", "Default Threshold Setting", "Effect"

   "threshold_logins_per_hour_per_system", "Limit the number of user logins per minute per system", "1000", "DELAY"
   "threshold_logins_per_hour_per_tenant", "Limit the number of user logins per minute per tenant", "10", "DELAY"
   "threshold_logins_per_hour_per_ip", "Limit the number of user logins per minute by the same IP address", "10", "DELAY"
   "threshold_logins_per_hour_per_tenant_per_ip", "Limit the number of user logins per minute per tenant by the same IP address", "5", "DELAY"
   "threshold_reports_per_hour_per_system", "Limit the number of reports that can be filed per hour per system", "1000", "BLOCK"
   "threshold_reports_per_hour_per_tenant", "Limit the number of reports that can be filed per hour per tenant", "10", "BLOCK"
   "threshold_reports_per_hour_per_ip", "Limit the number of reports that can be filed per hour by the same IP address", "10", "BLOCK"
   "threshold_reports_per_hour_per_tenant_per_ip", "Limit the number of reports that can be filed per hour per tenant by the same IP address", "5", "BLOCK"
   "threshold_attachments_per_hour_per_report", "Limit the number of attachments that can be uploaded per hour on a report", "30", "DELAY"
   "threshold_operations_per_hour_per_report", "Limit the number of operations that can be performed per hour on a report", "30", "DELAY"
   "threshold_operations_per_minute_per_report", "Limit the number of operations that can be performed per minute on a report", "20", "DELAY"
   "threshold_operations_per_second_per_report", "Limit the number of operations that can be performed per second on a report", "1", "DELAY"


In case of necessity, threshold configurations can be adjusted using the `gl-admin` command as follows:
::

  gl-admin setvar threshold_reports_per_hour_per_system 1

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
For scenarios where the whistleblower's trustworthiness has been validated or in projects with a low-risk threat model, the application offers an integrated file viewer. This viewer, leveraging modern browser sandboxing capabilities, allows the safe opening of a limited set of file types considered more secure than accessing files directly through the operating system.

The supported file formats are:

* AUDIO
* CSV
* IMAGE
* PDF
* VIDEO
* TXT

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

Entropy sources
---------------
The primary source of entropy for the platform is `/dev/urandom`.

UUIDv4 randomness
-----------------
System resources like submissions and files are identified by UUIDv4 to make them unguessable by external users and limit potential attacks.

TLS for smtp notification
-------------------------
All notifications are sent through an SMTP channel encrypted with TLS, using either SMTP/TLS or SMTPS, depending on the configuration.

Voice anonymization
-------------------
Whistleblowers can attach voice messages to their reports. To prevent a recording's acoustic fingerprint from exposing the source, the application anonymizes the speaker's voice entirely on the client and in real time: the microphone signal is processed in the browser through the `Web Audio API <https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API>`__ and only the transformed audio is ever recorded or uploaded, so the original voice never leaves the whistleblower's device.

The transformation is a classic analysis-and-synthesis `channel vocoder <https://en.wikipedia.org/wiki/Vocoder>`__ (Dudley, 1939): the signal is split into log-spaced constant-Q frequency bands, the slow amplitude envelope of each band is extracted, and that envelope drives an independent fixed-frequency carrier (a sine in the speech range, band-limited noise in the fricative range). Re-synthesizing speech from the band envelopes alone discards the fundamental frequency (pitch) and the glottal excitation rather than merely warping them, which is what makes the operation largely one-way. The formants are further disguised by a per-recording non-affine frequency warp that shifts the carrier bands by different amounts across the spectrum, so the formants do not all move by a single common ratio; this is only a secondary measure, since the anonymity comes from discarding the pitch and excitation rather than from relocating the formants.

This information-destroying design is intentionally stronger than reversible formant-only techniques such as the McAdams-coefficient transform (Patino et al., 2021), which preserve the excitation residual and therefore leak pitch and prosody. The method and its evaluation context follow the framing of the `VoicePrivacy Challenge <https://arxiv.org/abs/2404.02677>`__ (Tomashenko et al., 2024), the community reference benchmark for speaker anonymization.

This is best-effort signal-processing anonymization, intended to raise the bar rather than to guarantee unlinkability. It is effective against human recognition and naive automatic speaker verification, but, like the VoicePrivacy McAdams baseline (system B2), it offers only moderate protection against a strong, informed adversary. A single-factor vocal-tract-length normalization cannot invert a frequency-dependent warp, but an attacker fitting a flexible non-affine warp could still partially recover the formants, and speaking rate, rhythm and other prosodic habits still carry identity regardless. Stronger neural approaches (x-vector resynthesis or ASR-to-TTS pipelines) are not currently feasible in real time in the browser.
