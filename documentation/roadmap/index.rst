Project roadmap
===============

.. NOTE::
  This tentative roadmap is built by the GlobaLeaks team in order to try to respond to main users' needs. Please get sure that the needs of your projects and users are well represented on the project `Ticketing System <https://github.com/globaleaks/globaleaks-whistleblowing-software/issues>`_. If your organization could fund the development of parts of this roadmap please write us at info@globaleaks.org

Introduction
------------
This document details the main areas of research development and represents the actual tentative readmap of consolidation planned for 2024-2026 based on the analysis of the large set of user needs collected within the official `Ticketing System <https://github.com/globaleaks/globaleaks-whistleblowing-software/issues>`_.

Development areas
-----------------

Statistics and reporting
........................
GlobaLeaks still misses the implementation for any generation of statistics and reports. Such features are considered fundamental in order to properly support users in analysis, investigation and reporting.

E.g:

- Recipients should be able to visually see statistics about the received reports received and the data contained; these statistics should empower users in their work providing relevant information out of the data collection that could help users analyze and study social problems like corruption and be able to organize and export automatic reporting;
- Administrators should be able to visually see a dashboard in order to monitor the system and assure that all is working well (e.g. that recipients are receiving submissions and are able to access them and that no attacks are performed on the system).

Ideas:

- A client library could be adopted to generate reports directly on the client (e.g. Chart.js)
- The implementation should support the possibility of exporting the report in PDF; in relation to this aspect it should be considered the advantages of a possible backend implementation.

Reference tickets:

- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/1959
- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2254


Audit log
.........
GlobaLeaks still misses the implementation of a complete audit logit. This is considered a fundamental feature in order to achieve full accontability of the whistleblowing process and increase security.

Ideas:

- Software audit log should be improved
- The software could exposes a standard log interfaces in CEF/LEEF/Syslog format to foster integration with third party SIEM software.

Reference tickets:

- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2579
- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2580
- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2651

GDPR compliance
...............
GlobaLeaks implements by-design many best practices in matters of privacy and security.
In order to be effectively accepted and competitive beside commercial proprietary solutions and to guarantee the sustainability of the project, the software needs to achieve some market “standards” (e.g. GDPR compliance / ISO certifications / etc.); among all we selected that GDPR compliance is a first step where the software could implement best practices (e.g. procedures for self signup should present appropriate legal notices, terms of services, and contractualization). Within the software, there should be implemented an automatic contract generation via PDF or other suitable formats in respect with the GDPR requirements.

Reference tickets:

- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2145
- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2658
- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2866
- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2767
- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/3011
- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/3012

Backup and restore
..................
GlobaLeaks currently misses any feature for performing backup and restoring of its setup. These duties are currently performed by its users following typical best manual practices (e.g. archiving the data directory of the application). This project idea is to research the best practices to be applied in this context and to identify suitable strategies for implementing periodic, secure and encrypted backups to be restored upon necessity.

Reference tickets:

- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/528
- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2149

Multitenancy
............
Import and export of tenants
............................
Part of the software is a recent feature of Multitenancy, first implemented in 2018 and stabilized during 2019. Through this feature, GlobaLeaks makes it possible to create multiple setups of itself via virtual sites (similarly to Wordpress multisite feature).
In order to make it more easy for an administrator to migrate a platform form a system to an other or to enable users to require data portability from a globaleaks provider to an other, for example in relation to GDPR it has been evaluated necessary to improve the multi tenancy implementation by implementing support for import-export of tenants.
In the context of a whistleblowing application, involving encryption and logging this poses important challenges on how to best handle this process.

Reference tickets:

- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2632
- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2631

Multisite users
---------------
(To be further researched)

Important requirement at the base of the Multitenancy expansion is the possibility to enable users to be administrators and recipients of two or multiple instances running on the same multi-site setup.
This is useful for example when a lawyer takes part as a recipient on multiple projects; as well it is useful when an ICT consultant joins consultancy on multiple projects.

This could significatively simplify user access enabling the user to have a single set of username and password and associated keys.

References tickets:

- https://github.com/globaleaks/globaleaks-whistleblowing-software/issues/2302
