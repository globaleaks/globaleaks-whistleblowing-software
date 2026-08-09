Hello Matt,

Thank you very much for your report and for the detailed proof of concept.

We confirm the behavior you described: on the recipient report listing endpoint, a recipient who belongs to a non-selectable context/channel may receive the report objects of that channel even without an explicit `ReceiverTip` assignment, and for **unencrypted** reports the submitted answers are not redacted the way they are for encrypted ones. As it happens, we had just identified this same behavior during an internal audit and were already working on the correction, so your report is a very welcome and timely confirmation of our own findings.

That said, we would like to put the real-world impact into context:

- Since **release 3.0.0 (February 2018)**, GlobaLeaks enforces encryption on all platforms. Reports are stored encrypted by default, and the answers of a report a recipient is not assigned to are already blanked (the `crypto_tip_pub_key` branch). We therefore expect that in practice there are no longer active platforms holding unencrypted submissions, which limits this issue to legacy/manually-altered configurations.

- Even in that residual scenario, the exposure is limited to users who are already authenticated and authorized recipients within the same organization/channel — i.e. parties that are trusted according to our threat model — rather than to unauthenticated or external actors.

For these reasons we assess the practical severity as **low**. Nonetheless, the fix is straightforward and correct to make, so we are preparing a patch that redacts answers and labels for any report the current recipient is not assigned to, independently of the encryption setting.

We are also proceeding with a security advisory and a CVE request. If it works for you, we would publish the official advisory crediting you by the **end of July**, together with the batch of other CVEs we have recently prepared.

Thanks again for the responsible disclosure and for helping us improve GlobaLeaks.

Best regards,
Giovanni
