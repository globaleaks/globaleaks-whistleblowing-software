# Channel recipients could read unencrypted non-assigned reports

## Summary
The `/api/recipient/rtips` endpoint of GlobaLeaks lists, to a recipient who is a member of a channel, the reports of that channel — by design — including reports the recipient is not explicitly assigned to. For such non-assigned reports the recipient is entitled only to the **metadata**, not to the contents, until access is granted through the platform workflow. However, the redaction of the submitted answers and label is applied only to encrypted reports, so on legacy platforms installed before release 3.0.0 (February 2018) that still host unencrypted reports the contents of non-assigned reports could be disclosed to a recipient of the same channel.

## Affected Versions
GlobaLeaks versions ≤ 5.0.96 are affected for the metadata-listing behavior.
The content-disclosure part additionally requires report encryption to be disabled, a condition that can only occur on setups installed before version 3.0.0 (2018), the release since which GlobaLeaks enforces encryption on all platforms.
Remediation and proper redaction are implemented in version 5.0.97 and later.

## Details
- Recipients connected to a channel are intentionally allowed to list all the reports of that channel, so that access to an individual report can be requested/granted through the platform workflow. Each report is returned with an `accessible` flag indicating whether the current recipient holds an explicit `ReceiverTip` assignment.
- For reports the recipient is not assigned to (`accessible == false`), the answers and label are supposed to be omitted. This redaction was implemented only within the encrypted-report branch (`crypto_tip_pub_key`). As a consequence, for **unencrypted** reports — a non-default configuration — the answers and label remained populated in the API response even when `accessible` was false.
- On platforms with encryption enabled (the enforced default), the answers of non-assigned reports are already blanked, and the exposure is limited to report metadata that is, by design, part of the channel listing feature.

## Proof of Concept (PoC)
On a platform with report encryption disabled, a recipient (`recipient_b`) who is a member of a channel but is not assigned to a given report authenticates and requests:

```
GET /api/recipient/rtips HTTP/1.1
Host: <platform>
X-Session: <recipient_b_session>
DPoP: <valid_dpop_proof>
Accept: application/json
```

The listing includes the non-assigned report flagged `"accessible": false`, while — on the unencrypted configuration — also returning the submitted `answers` in plaintext.

## Impact
- Technical Impact on GlobaLeaks: None. The endpoint does not execute code, modify platform data, or expose credentials.
- User Impact: Limited. The only actor able to exploit this behavior is a user already provisioned in the system as a recipient of the affected channel. Such a recipient is, by design, authorized to list the **metadata** of all reports of their channel — so that access to an individual report can be requested and granted through the platform workflow — but is **not** entitled to the **contents** (answers, label, attachments) of reports they have not been explicitly assigned to; a report's content becomes accessible to a recipient only after they are added to it. The incomplete redaction therefore did cross an intended authorization boundary: on encryption-disabled platforms it returned the answers and label of non-assigned reports to a recipient who had not been granted access to them. Exploitation is nonetheless limited to an authenticated recipient acting within their own channel and is never exposed to unauthenticated or external actors.
- Metadata: The listing of report metadata for a channel is an intended feature for members of the channel and does not by itself constitute the vulnerability.
- Content disclosure: The disclosure of submitted answers to a non-assigned recipient is possible only when report encryption is disabled. GlobaLeaks has enforced encryption on all platforms since release 3.0.0 (February 2018); unencrypted platforms are therefore not expected to exist in practice, restricting real-world impact to legacy or manually-altered configurations.
- Required Preconditions: A non-default configuration with encryption disabled, plus a valid authenticated recipient account within the affected channel.

## Vulnerability Classification
- CWE: CWE-863 - Incorrect Authorization
- CVSS v3.1 Base Score: 3.7 (Low)

CVSS Metrics:
- Attack Vector (AV): Network (N) - Input is submitted via the network.
- Attack Complexity (AC): High (H) - Exploitation for content disclosure requires a non-default configuration with encryption disabled and a specific channel setup.
- Privileges Required (PR): Low (L) - A valid authenticated recipient account is required.
- User Interaction (UI): None (N).
- Scope (S): Unchanged (U).
- Confidentiality (C): Low (L) - Limited to reports within the recipient's own channel, and to report contents only on encryption-disabled platforms.
- Integrity (I): None (N) - No system data can be modified.
- Availability (A): None (N) - System availability is unaffected.

## Mitigation and Recommendations
- Keep report encryption enabled (the enforced default), which already prevents content disclosure for non-assigned reports.
- Upgrade to version 5.0.97 or later, where answers and label are redacted for any report the current recipient is not assigned to, independently of the encryption setting.

## Conclusion
The reported issue represents a low-risk vulnerability: no code execution, no data modification, and no service disruption is possible. The metadata listing is an intended feature scoped to authenticated members of the same channel, and content disclosure is possible only on non-default, encryption-disabled configurations that are not expected to exist on platforms provisioned since release 3.0.0 (February 2018). The fix ensures answers and labels are consistently redacted for non-assigned reports regardless of the encryption setting.

## Timeline
2026-07-06: Vulnerability reported
2026-07-06: Vulnerability analyzed
2026-07-XX: Fix developed and internally validated
2026-07-XX: CVE requested
2026-07-XX: Remediation released in version 5.0.97
2026-07-XX: Public advisory published

## Credits
- Finder and reporter: Matt Mumford (mattmumford-git)
- Analysts: evilaliv3, vecna, cyberflaneuse, naif
