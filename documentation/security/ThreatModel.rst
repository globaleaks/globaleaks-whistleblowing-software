============
Threat model
============
GlobaLeaks is a free and open-source whistleblowing software designed for various usage scenarios, each requiring a balance between strong security and high usability. These two requirements are crucial for managing whistleblowing procedures effectively, protecting whistleblowers, and achieving specific project goals. Given the variety of use cases and associated risks, the software can be configured to address the specific threat model detailed here.

This document is intended for organizations implementing a whistleblowing procedure using GlobaLeaks. It supports the analysis and understanding of the specific threat model relevant to their context and risks and guides users in selecting best practices for their project.

Users matrix
============
The first step is to define the types of users interacting with a GlobaLeaks platform.

.. csv-table::
   :header: "User", "Definition"

   "Whistleblower", "The user who submits an anonymous report through the platform. Whistleblowers may operate under various threat models depending on the usage scenario and the nature of the information submitted."
   "Recipient", "The user who receives and analyzes anonymous reports from Whistleblowers. Recipients act in good faith and are considered trusted parties concerning the protection of Whistleblowers' confidentiality."
   "Administrator", "Users responsible for setting up, managing, and monitoring the platform's security. Administrators may not be the same entities running or managing the whistleblowing initiatives (e.g., hosted solutions, multiple stakeholder projects). Administrators are trusted entities but do not have direct access to reports and advise Recipients on best practices."

It is crucial to apply security measures relative to the users of the platform, aiming to achieve an appropriate tradeoff between security and usability.

Anonymity matrix
================
The anonymity of users must be classified depending on the context of use, as follows:

.. csv-table::
   :header: "User", "Definition"

   "Anonymous", "The user accesses the platform via the Tor Browser and follows best practices to protect their identity, minimizing the risk of tracking by any system involved in the operation. The user has not disclosed their identity to Recipients."
   "Confidential", "The user accesses the platform via a common browser. While third parties might log their IP address, the platform protects the content of their communication. The user may choose to disclose their identity to Recipients confidentially."

The platform always informs users of their current anonymity status and provides guidance on best practices for anonymous access via the Tor Browser. Administrators may enforce the requirement that Whistleblowers use the Tor Browser to file reports, depending on the use case.

Communication security matrix
=============================
The security of communication concerning third-party monitoring varies based on the context of use.

.. csv-table::
   :header: "Security level", "Description"

   "High security", "Tor is used, and communication is encrypted end-to-end with the GlobaLeaks platform, ensuring that no third party can eavesdrop on the communication."
   "Medium security", "HTTPS is used, and communication is encrypted end-to-end with the GlobaLeaks platform. A third party capable of manipulating HTTPS security (e.g., re-issuing TLS certificates) could eavesdrop on the communication. If HTTPS security is maintained, monitoring the user's communication line or the GlobaLeaks platform's communication line is not feasible."

Identity disclosure matrix
==========================
Regardless of the anonymity matrix, users may choose or be required to disclose their identity.

.. csv-table::
   :header: "Identity disclosure matrix", "Definition"

   "Undisclosed", "The user's identity is not disclosed and is unlikely to be disclosed."
   "Optionally disclosed", "The user's identity is not disclosed by default but may be voluntarily disclosed (e.g., an anonymous tip-off MAY receive a follow-up, whereas a formal report with disclosed identity MUST receive a follow-up)."
   "Disclosed", "The user chooses or is required to disclose their identity to other users."

Identity disclosure is crucial because even in an Anonymous High security environment, disclosing one's identity may be a valuable option for specific whistleblowing workflows.

Users starting with an anonymity setting of “Anonymous” and an “Undisclosed Identity” can decide later to disclose their identity. Conversely, this cannot be undone. This consideration is key to ensuring user protection in GlobaLeaks.

Voluntary identity disclosure may be required in certain whistleblowing procedures because:

* A tip-off MAY receive a follow-up and can be anonymous;
* Formal reports MUST receive a follow-up and cannot be anonymous.

The distinction between “MAY” and “MUST” refers to the actions of recipients and is a fundamental element of the guarantees provided to whistleblowers in many initiatives (e.g., a corporate or institutional whistleblowing platform should not follow a MUST approach for anonymous submission follow-up, treating such submissions as tip-offs rather than formal reports).

Usage scenarios matrix
======================
This section provides examples of how different anonymity levels for users can be combined depending on the context of use.

.. csv-table::
   :header: "Use case", "Description"

   "Media outlet", "A media outlet with a disclosed identity initiates a whistleblowing project. The outlet’s recipients are disclosed to Whistleblowers, allowing them to trust a specific journalist rather than the outlet itself. Full anonymity must be assured to whistleblowers, and their identity cannot be disclosed in connection with anonymous submissions. Whistleblowers MAY choose to disclose their identity if they trust the journalist's source-protection record."
   "Corporate compliance", "A corporation implements transparency or anti-bribery law compliance by promoting initiatives to employees, consultants, and providers. Recipients are part of a company division (e.g., Internal Audit office). Whistleblowers are guaranteed full anonymity but may optionally disclose their identity."
   "Human Rights Activism Initiative", "A human rights group initiates a whistleblowing project to expose violations in a dangerous area. The organization requires anonymity to avoid retaliation and operates under a pseudonym. Recipients MUST not be disclosed to Whistleblowers, but partial disclosure by pseudonym is acceptable to establish trust. The Whistleblower MUST be guaranteed anonymity and their identity cannot be disclosed."
   "Citizen media initiative", "A citizen media initiative with a public identity seeks reports on specific topics (e.g., political, environmental malpractice, corruption) in a medium-low risk operational context. Recipients may use pseudonyms or remain public to avoid complete exposure. Whistleblowers, if the topic is not life-threatening, may submit reports confidentially to lower the entry barrier."

The following matrix illustrates how different usage scenarios can require various anonymity levels, communication security requirements, and identity disclosures for different users.

GlobaLeaks will provide appropriate security awareness information through its user interface and enforce specific requirements based on clear configuration guidelines.

.. csv-table::
   :header: "Scenario", "User", "Anonymity level", "Identity disclosure", "Communication security"

   "Media outlet", "Whistleblower", "Anonymous", "Undisclosed", "High security"
   "", "Recipient", "No anonymity", "Disclosed", "Medium security"
   "", "Admin", "No anonymity", "Disclosed", "Medium security"
   "Corporate compliance", "Whistleblower", "Anonymous", "Optionally disclosed", "High security"
   "", "Recipient", "No anonymity", "Partially disclosed", "Medium security"
   "", "Admin", "No anonymity", "Disclosed", "Medium security"
   "Human Rights Activism Initiative", "Whistleblower", "Anonymous", "Undisclosed", "High security"
   "", "Recipient", "Anonymous", "Partially disclosed", "High security"
   "", "Admin", "Anonymous", "Partially disclosed", "High security"
   "Citizen media initiative", "Whistleblower", "Confidential", "Optionally disclosed", "Medium security"
   "", "Recipient", "Confidential", "Confidential", "Medium security"
   "", "Admin", "No anonymity", "Disclosed", "Medium security"

Data security matrix
====================
This section highlights the data handled by GlobaLeaks and the protection schemes applied to it.

The following information types are involved in GlobaLeaks:

.. csv-table::
   :header: "Information type", "Description"

   "Questionnaire answers", "Data associated with a submission, including the filled forms and options selected by the Whistleblower."
   "Submission attachments", "Files associated with a submission."
   "Platform configuration", "Data for configuring and customizing the platform."
   "Software files", "All files required for the software to function, including default configurations."
   "Email notifications", "Data sent to notify recipients of new reports via email."

Below is a matrix showing the different security measures applied to data.

.. csv-table::
   :header: "Information type", "Encryption", "Filters", "Sanitization"

   "Questionnaire answers", "Encrypted in the database with per-user/per-submission keys", "Keyword filters", "Antispam, Anti-XSS"
   "Submission attachments", "Encrypted on the filesystem with per-user/per-submission keys", "Extension blocking, Antivirus", "N/A"
   "Email notifications", "Encrypted with PGP when recipient keys are available", "Antispam to prevent flooding", "N/A"

Threats to anonymity and confidentiality
========================================
This section highlights various threats that require specific consideration.

Browser history and cache
-------------------------
GlobaLeaks uses crafted HTTP headers and other techniques to minimize leaking information into a user’s browser history or cache. While this privacy feature enhances safety, it cannot guarantee protection against forensic analysis of browser cache and history but serves as an additional safety measure.

Metadata
--------
Files may contain metadata related to the author or whistleblower. Cleaning metadata from submitted files helps protect an "unaware" whistleblower from inadvertently including information that may compromise their anonymity. GlobaLeaks does not automatically clean metadata by default, as metadata is considered a fundamental part of the original evidence that should be preserved. Metadata cleanup is an optional step that may be suggested to Whistleblowers or performed by Recipients when sharing documents with others. When sharing files with external parties, Recipients are advised to print the document and provide a hard copy to ensure that only visible information is shared, avoiding the risk of sharing sensitive metadata. For more on metadata and redacting digital files, see the article `Everything you wanted to know about media metadata, but were afraid to ask <https://freedom.press/training/everything-you-wanted-know-about-media-metadata-were-afraid-ask/>`_ by Harlo Holmes. A useful tool for these procedures is the `Metadata Anonymization Toolkit <https://0xacab.org/jvoisin/mat2>`_.

Malware and trojans
-------------------
GlobaLeaks cannot prevent an attacker from using the platform maliciously to target recipients with malware or trojans. To mitigate risks of data exfiltration through trojans, Recipients should implement proper operational security by using dedicated laptops for report viewing and opening file attachments on offline computers. Wherever possible, they should use specialized secure operating systems like `QubesOS <https://www.qubes-os.org/>`_ or `Tails <https://tails.boum.org/>`_ and ensure up-to-date antivirus software is running.

Network and reverse proxies
---------------------------
GlobaLeaks is designed for use with direct Tor or TLS connections from the user’s browser to the application backend. The use of Network and Reverse Proxies in front of the application is discouraged as they can interfere with the application and compromise confidentiality and anonymity measures implemented in GlobaLeaks.

Data stored outside the platform
--------------------------------
GlobaLeaks does not provide security for data stored outside the GlobaLeaks system. It is the responsibility of Recipients to protect data downloaded from the platform or shared via external USB drives. The operating system used or the USB drive should offer encryption to ensure that, in case of device loss or theft, the data remains inaccessible.

Environmental factors
---------------------
GlobaLeaks does not protect against environmental factors related to users' physical locations or social relationships. For example, if a user has a surveillance device in their home, GlobaLeaks cannot provide protection. Similarly, if a whistleblower, who is supposed to be anonymous, shares their story with friends or coworkers, GlobaLeaks cannot offer protection.

Incorrect data retention policies
---------------------------------
GlobaLeaks implements a strict default data retention policy of 90 days to allow users to manage reports within a limited time frame necessary for investigations. If the platform is configured to retain reports for an extended period and Recipients do not manually delete unnecessary reports, the value of the data increases, along with the risk of exposure.

Human negligence
----------------
While GlobaLeaks provides Administrators with the ability to fine-tune security configurations and continuously informs users about their security context, it cannot protect against major security threats resulting from human negligence. For instance, if a Whistleblower submits data that can identify them as the unique owner or recent viewer, GlobaLeaks cannot protect their identity.

Advanced traffic analysis
-------------------------
An attacker monitoring HTTPS traffic, without the ability to decrypt it, can still identify user roles based on different network traffic patterns generated by Whistleblowers, Recipients, and Administrators. GlobaLeaks does not offer protection against this type of threat. We recommend using `Tor pluggable transports <https://2019.www.torproject.org/docs/pluggable-transports.html.en>`_ or other methods that provide additional protection against such attacks.
