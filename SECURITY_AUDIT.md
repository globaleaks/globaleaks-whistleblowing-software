### Security Audit Report: Security Headers Assessment on Demo Instances

As part of the Security Audit task (#4430), I conducted an initial automated evaluation of the public demo instances (`https://try.globaleaks.org`) focusing on server-side security configurations and HTTP security headers.

#### Findings Summary
The target instance demonstrates an exemplary security posture, achieving the highest rating (**A+**) on infrastructure hardening tests. 

| Security Header | Status | Configuration / Policy |
| :--- | :--- | :--- |
| **Strict-Transport-Security (HSTS)** | ✅ Secured | `max-age=31536000; includeSubDomains; preload` |
| **Content-Security-Policy (CSP)** | ✅ Secured | Strict object-src, script-src, and frame-ancestors definitions configured. |
| **X-Frame-Options** | ✅ Secured | `deny` (Full clickjacking protection) |
| **X-Content-Type-Options** | ✅ Secured | `nosniff` (MIME-sniffing protection) |
| **Permissions-Policy** | ✅ Secured | Restrictive control over browser features & device APIs. |
| **Referrer-Policy** | ✅ Secured | `no-referrer` |

#### Additional Observations
* **Onion-Location**: The server properly advertises its Tor Onion service via the `Onion-Location` header, ensuring cross-origin seamless routing for privacy-centric users.
* **Cache-Control**: `no-store` is strictly enforced to avoid sensitive data retention on client-side storage.

#### Conclusion
The web infrastructure of GlobaLeaks' demo instances follows industry best practices for mitigating common web vulnerabilities such as Cross-Site Scripting (XSS), Clickjacking, and MIME-sniffing attacks. No missing core security headers or misconfigurations were identified during this phase of the audit.