Features
========

User features
-------------

- Multi-user system with customizable user roles (whistleblower, recipient, administrator)
- Fully manageable via a web administration interface
- Allows whistleblowers to decide if and when to confidentially declare their identity
- Facilitates multimedia file exchanges with whistleblowers
- Secure management of file access and visualization
- Enables chat with whistleblowers to discuss reports
- Provides a unique 16-digit receipt for anonymous whistleblower login
- Simple recipient interface for receiving and analyzing reports
- Supports report categorization with labels
- Includes user search functionality for reports
- Supports the creation and assignment of case management statuses
- Customizable appearance (logo, color, styles, font, text)
- Allows defining multiple reporting channels (e.g., by topic, department)
- Enables creation and management of multiple whistleblowing sites (e.g., for subsidiaries or third-party clients)
- Advanced questionnaire builder
- Provides whistleblowing system statistics
- Support for `more than 70 languages <https://www.transifex.com/otf/globaleaks>`_ and Right-to-Left (RTL) languages

Legal features
--------------

- Designed in adherence to `ISO 37002:2021 <https://www.iso.org/standard/65035.html>`_ and `Directive (EU) 2019/1937 <https://eur-lex.europa.eu/legal-content/en/TXT/?uri=CELEX%3A32019L1937>`_ recommendations for whistleblowing compliance
- Supports bidirectional anonymous communication (comments/messages)
- Customizable case management workflow (statuses/sub-statuses)
- Conditional reporting workflow based on whistleblower identity
- Manages conflicts of interest in the reporting workflow
- Custodian functionality to authorize access to whistleblower identity
- GDPR privacy by design and by default
- Configurable GDPR data retention policies
- GDPR-compliant subscriber module for new SaaS users
- No IP address logging
- Includes an audit log
- Integrates with existing enterprise case management platforms
- Free Software OSI Approved `AGPL 3.0 License <https://github.com/globaleaks/globaleaks-whistleblowing-software/blob/stable/LICENSE>`_

Security features
-----------------

- Designed in adherence to `ISO 27001:2022 <https://www.iso.org/standard/82875.html>`_, `General Data Protection Regulation (EU) 2016/679 <https://eur-lex.europa.eu/eli/reg/2016/679/oj>`_, `CSA STAR <https://cloudsecurityalliance.org/star>`_, and `OWASP <https://owasp.org/>`_ recommendations for privacy and security compliance
- Full data encryption for whistleblower reports and recipient communications
- Supports digital anonymity through `Tor <https://www.torproject.org/>`_ integration
- Built-in HTTPS support with `TLS 1.3 <https://tools.ietf.org/html/rfc8446>`_ standard and `SSLabs A+ <https://www.ssllabs.com/ssltest/analyze.html?d=try.globaleaks.org>`_ rating
- Automatic enrollment for free digital certificates with `Let’s Encrypt <https://letsencrypt.org/>`_
- Multiple penetration tests with publicly available reports
- Two-Factor Authentication (2FA) compliant with `TOTP RFC 6238 <https://tools.ietf.org/html/rfc6238>`_
- Integrated network sandboxing with iptables
- Application sandboxing with `AppArmor <http://wiki.apparmor.net/>`_
- Complete protection against automated submissions (spam prevention)
- Continuous peer review and periodic security audits
- PGP support for encrypted email notifications and file downloads
- Leaves no traces in browser cache

Technical features
------------------

- Designed in adherence to `ISO 27001:2022 <https://www.iso.org/standard/82875.html>`_, `Directive (EU) 2019/882 <https://eur-lex.europa.eu/legal-content/IT/TXT/?uri=CELEX%3A32019L0882>`_, `Directive (EU) 2016/2102 <https://eur-lex.europa.eu/legal-content/IT/TXT/?uri=CELEX%3A32016L2102>`_, `W3C WCAG 2.2 <https://www.w3.org/TR/WCAG22/>`_, and `WAI-ARIA 2.2 <https://www.w3.org/TR/wai-aria-1.2/>`_ recommendations for accessibility compliance
- Multi-site support enabling the operation of multiple virtual sites on the same setup
- Responsive user interfaces created with `Bootstrap <https://getbootstrap.com/>`_ CSS framework
- Automated software quality measurement and continuous integration testing
- Long-Term Support (LTS) plan
- Built with lightweight framework technologies (`Angular <https://angular.dev/>`_ and `Python Twisted <https://twisted.org/>`_)
- Integrated `SQLite <https://sqlite.org>`_ database
- Automatic setup for `Tor Onion Services Version 3 <https://www.torproject.org/>`_
- Supports self-service signup for whistleblowing SaaS setup
- Compatible with Linux operating systems (`Debian <https://www.debian.org/>`_ / `Ubuntu <https://ubuntu.com/>`_)
- Debian packaging with a repository for updates/upgrades
- Fully self-contained application
- Easy integration with existing websites
- Built and packaged with `reproducibility <https://en.wikipedia.org/wiki/Reproducible_builds>`_ in mind
- REST API
