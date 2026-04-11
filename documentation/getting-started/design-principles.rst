Design principles
=================

Whistleblowers play a crucial role in safeguarding accountability, transparency, and integrity within organizations and society. Often operating from vulnerable positions and facing professional, legal, or personal risks, they may be entitled to protection under the laws of their country. To empower their actions and ensure effectiveness, digital whistleblowing systems should be designed according to strong principles of protection, privacy, accessibility, scalability, and sustainability.

To put these principles into practice, such systems should aim to comply with international regulations [1]_ and recognized industry standards [2]_, ensuring that reports are securely received, properly acknowledged, and effectively followed up. At the same time, the system should implement best practices promoted by leading whistleblower protection organizations [3]_ [4]_ [5]_, providing a trustworthy, transparent, and safe environment for both whistleblowers and recipients of reports.

Key principles and objectives:

- `Security, and privacy and anonymity <security-privacy-anonymity_>`_
- `Accessibility, internationalization and inclusivity <accessibility-internationalization-inclusivity_>`_
- `Flexibility and scalability, interoperability <flexibility-scalability-interoperability_>`_
- `Open-Source, sustainability and digital sovereignty <opensource-sustainability-digitalsovereignty_>`_

.. _security-privacy-anonymity:

Security, and privacy and anonymity
-----------------------------------
To minimize the risk of design flaws and implementation errors, systems should adopt well-known and internationally recognized security standards [6]_ [7]_. Implemented encryption protocols in any component should aim at perfect-forward-secrecy (PFS), end-to-end (E2EE), zero-knowledge design. Role-based access control (RBAC), robust authentication mechanisms, and comprehensive audit logs are essential to maintain data integrity, traceability, and accountability across all processes. In line with the Zero-Trust paradigm [8]_, the architecture should assume that no user, device, or network can be inherently trusted and support continuous verification, strong identity management, and segmentation of data.

The handling of sensitive information should comply with international data protection regulations implementing privacy by design and by default [9]_ and ensure secure handling of sensitive information throughout the complete data workflow and lifecycle. Data collection and retention should be limited to the minimum necessary to achieve the system’s objectives. The implementation should aim to guarantee maximum confidentiality of any data exchanges and support the possibility of technical anonymity (e.g. by means of Tor) [10]_.
Under no circumstances shall the system integrate with or share data with third parties, unless the whistleblower has provided explicit, informed, and verifiable consent, and any third-party processing is strictly limited to the purpose for which consent was granted.

Objectives:

- Protects sensitive reports from interception or manipulation;
- Limits long-term liability by avoiding unnecessary data retention;
- Ensures accountability and traceability of system use;
- Strengthens the credibility of the system through demonstrable privacy and security safeguards.

.. _accessibility-internationalization-inclusivity:

Accessibility, internationalization and inclusivity
---------------------------------------------------
To ensure that all individuals, regardless of language, ability, or device, the system should comply with accessibility standards, offering a multilingual, responsive, and user-friendly experience [11]_ [12]_. The system’s design and terminology, as well as its documentation, should prioritize inclusivity [13]_.

Objectives:

- Ensures equal access for all users, including those with disabilities;
- Expands the reach of the system across diverse user groups;
- Demonstrates a commitment to inclusivity and fairness.

.. _flexibility-scalability-interoperability:

Flexibility and scalability, interoperability
---------------------------------------------
To ensure the system can meet evolving organizational needs and handle increasing reporting volumes efficiently, systems should support secure data segregation, integration with management tools, and interoperability through open standards and APIs. They should aim at scaling dynamically in cloud or hybrid deployments without compromising performance, security, or compliance.

Objectives:

- Adapts to growing reporting volumes without performance loss;
- Improves operational efficiency through seamless data flows;
- Supports long-term sustainability and avoiding technical lock-in.

.. _opensource-sustainability-digitalsovereignty:

Open Source, sustainability and digital sovereignty
---------------------------------------------------

To support long-term sustainable digital practices and development goals [14]_, preference should be given to open-source software or components that are published and reviewed in accountable Digital Public Catalogues [15]_ [16]_. Where such options are unavailable, the system should rely on trustworthy technologies or providers. This approach helps reduce dependence on proprietary vendors, increases transparency and trust for end users, and strengthens digital sovereignty [17]_. In all cases the system should include a comprehensive and up-to-date Software Bill of Materials (SBOM) [18]_ to provide visibility into software dependencies, facilitate independent security audits [19]_, enable interoperability, and ensure long-term compliance and sustainability of the system.

Objectives:

- Ensures long-term transparency and public accountability;
- Reduces dependency on proprietary vendors;
- Contributes to global efforts for sustainable and equitable digital infrastructure.

.. [1] `DIRECTIVE (EU) 2019/1937 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL  of 23 October 2019  on the protection of persons who report breaches of Union law <https://eur-lex.europa.eu/eli/dir/2019/1937/oj/eng>`_
.. [2] `ISO 37002:2021 – Whistleblowing Management Systems <https://www.iso.org/standard/65035.html>`_
.. [3] `Whistleblowing International Network (WIN) <https://whistleblowingnetwork.org>`_
.. [4] `Overview of whistleblowing software. U4 Helpdesk Answer 2020:04. Transparency International <https://knowledgehub.transparency.org/assets/uploads/helpdesk/Overview-of-whistleblowing-software_2020_PR.pdf>`_
.. [5] `Freedom of the Press Foundation (FPF) <https://freedom.press/>`_
.. [6] `ISO/IEC 27001:2022 – Information Security Management <https://www.iso.org/standard/27001>`_
.. [7] `OWASP Guidelines – Secure Software Development Practices <https://owasp.org/>`_
.. [8] `NIST SP 800-207 – Zero Trust Architecture <https://nvlpubs.nist.gov/nistpubs/specialpublications/NIST.SP.800-207.pdf>`_
.. [9] `Regulation (EU) 2016/679 – General Data Protection Regulation (GDPR) <https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng>`_
.. [10] `Tor Browser – Browser for anonymous and secure communication <https://www.torproject.org/>`_
.. [11] `DIRECTIVE (EU) 2019/882 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL  of 17 April 2019  on the accessibility requirements for products and services <https://eur-lex.europa.eu/eli/dir/2019/882/oj/eng>`_
.. [12] `DIRECTIVE (EU) 2016/2102 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL  of 26 October 2016  on the accessibility of the websites and mobile applications of public sector bodies <https://eur-lex.europa.eu/eli/dir/2016/2102/oj/eng>`_
.. [13] `IEEE 3400-2025 - IEEE Standard for Use of Inclusive Language in Technical Terminology and Communications <https://standards.ieee.org/ieee/3400/11579/>`_
.. [14] `UN Sustainable Development Goals (SDGs) <https://www.undp.org/sustainable-development-goals>`_
.. [15] `Digital Public Goods Registry <https://www.digitalpublicgoods.net/>`_
.. [16] `EU Open Source Solutions Catalogue <https://interoperable-europe.ec.europa.eu/eu-oss-catalogue>`_
.. [17] `Trust, Not Just Code: Why Digital Public Goods Catalogues Matter for Whistleblowing Software (2025). G.Pellerano on Whistleblowing International Network site <https://whistleblowingnetwork.org/Our-Work/Spotlight/Stories/Trust-Not-Just-Code>`_
.. [18] `Regulation (EU) 2024/2847 of the European Parliament and of the Council of 23 October 2024 on horizontal cybersecurity requirements for products with digital elements (Cyber Resilience Act) <https://eur-lex.europa.eu/eli/reg/2024/2847/oj/eng>`_
.. [19] `The pitfalls of closed-source whistleblowing software (2022). G.Pellerano on Whistleblowing International Network site <https://whistleblowingnetwork.org/Our-Work/Spotlight/Stories/The-Pitfalls-of-Closed-Source-Whistleblowing-Softw>`_
