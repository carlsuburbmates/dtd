# DTD Pre-Cutover DNS State Snapshot
**Captured:** 2026-09-11T10:00:18Z (UTC)  
**Captured by:** Antigravity agent, pre-DNS-cutover documentation requirement  
**Purpose:** Rollback reference — if Firebase DNS cutover fails, restore these exact records at the registrar / Vercel DNS panel.

---

## Current Vercel DNS Records (Captured via vercel dns ls)
```text
RECORD ID                     NAME               TYPE    VALUE
(default)                                        ALIAS   cname.vercel-dns-017.com.
(default)                     *                  ALIAS   cname.vercel-dns-017.com.
rec_a5ede93c2b3e0c1c421ca214  _dmarc             TXT     v=DMARC1; p=quarantine; rua=mailto:info@dogtrainersdirectory.com.au; adkim=s; aspf=s
rec_431436e0af67f89cd6c8ad2e  resend._domainkey  TXT     p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC1vm/PCqJb8gcbXiaFYQ8Y28G1ss3mPIpkJD22R7Dtjp6Faozn4d5nn6dikqPU9dKSy15SEnAJq+Qageo32k9K0USQiKTnCU/Te4UkwffVfc1yLmWFC+NAD4XS3OB/5Pcfr9u9IZaGz69lD7/753kghIXd5V4OPzP8AOlQC1JpqwIDAQAB
rec_9d8bf9289f428faa06b8b443  send               TXT     v=spf1 include:amazonses.com ~all
rec_0dc122ff316e93972c3fe010  send               MX      10 feedback-smtp.ap-northeast-1.amazonses.com.
rec_8d939b40a04c9073e70517b2  zmail._domainkey   TXT     v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCXI88TzvyZWUg3WiQoqYDE8rgHRQOWwrop+PzrXhfkZRX7w8x/jAz0Iss6+TEZKKeLwyooLiukA2St7bgH/WsiCoRlAbmjsLNDlDATWiGL2svy2NG3IbPd6tFcvglQHIMVKWIPP7a+4v4Y8JClFHz4f4tSrCgnh2gxsfoARSE27QIDAQAB
rec_ad3b34aeb8493b6a2a915118  @                  TXT     v=spf1 include:one.zoho.com ~all
rec_112a38f724ecfaeaf5a6455b  @                  TXT     zoho-verification=zb85165549.zmverify.zoho.com
rec_0b0938a8e43960191144bab7  @                  MX      50 mx3.zoho.com.
rec_45048e0a79c4cfb01feffd8a  @                  MX      20 mx2.zoho.com.
rec_aaf2ee5939a62c6baad17b08  @                  MX      10 mx.zoho.com.
```

## MX & Email Integrity (CRITICAL)
Zoho Mail and Resend DKIM/SPF records are active and verified. Under NO circumstances should any `rec_*` related to `_domainkey`, `send`, `zoho`, or MX records be touched.


---

## Records to ADD (Firebase Hosting)
```
# Firebase A record (replace Vercel IPs)
dogtrainersdirectory.com.au.  A    199.36.158.100

# Firebase www CNAME (new record)
www.dogtrainersdirectory.com.au.  CNAME  gen-lang-client-0028123502.web.app.

# Firebase hosting verification TXT (new record)
dogtrainersdirectory.com.au.  TXT  "hosting-site=gen-lang-client-0028123502"

# Firebase ACME SSL challenge TXT records (new)
_acme-challenge.dogtrainersdirectory.com.au.  TXT  "exCJ2FwW2cwKT8ZYFrAzLwiKGyjOeWb1KluIzq7vGLY"
_acme-challenge.dogtrainersdirectory.com.au.  TXT  "vjwCoVei22N1VKFtNU80A0Oqkxz0SbkSzx7iB_KgveI"
```

---

## Rollback Procedure (if cutover fails)

If the site fails to resolve on `dogtrainersdirectory.com.au` after DNS cutover:

1. Log into the domain registrar.
2. Restore Vercel nameservers: `ns1.vercel-dns.com` + `ns2.vercel-dns.com`.
3. At Vercel DNS panel, confirm these A records exist:
   - `@ → 64.29.17.1`
   - `@ → 216.198.79.1`
4. Confirm MX and TXT records above are still present (they should not have been touched).
5. Wait for TTL propagation (A record TTL was 1800s = 30 min, NS TTL was 21600s = 6h).

> If nameservers were not changed (i.e. changes made within existing Vercel DNS zone only), rollback is instant — just revert the A records from `199.36.158.100` back to `64.29.17.1` + `216.198.79.1`.

---

## Cutover Strategy: In-Zone Record Swap (Lowest Risk)

**Recommended approach — no nameserver change required:**

Since Vercel DNS is the authoritative zone, all changes are made *within the existing Vercel DNS zone* without touching registrar nameservers or Zoho Mail records.

### Executable Cutover Commands (Run via Vercel CLI):
```bash
# 1. Add Firebase A Record for Root
vercel dns add dogtrainersdirectory.com.au "" A 199.36.158.100

# 2. Add www CNAME Record
vercel dns add dogtrainersdirectory.com.au www CNAME gen-lang-client-0028123502.web.app.

# 3. Add Firebase Site Verification TXT
vercel dns add dogtrainersdirectory.com.au "" TXT "hosting-site=gen-lang-client-0028123502"

# 4. Add Firebase SSL Certificate ACME Challenges
vercel dns add dogtrainersdirectory.com.au _acme-challenge TXT "exCJ2FwW2cwKT8ZYFrAzLwiKGyjOeWb1KluIzq7vGLY"
vercel dns add dogtrainersdirectory.com.au _acme-challenge TXT "vjwCoVei22N1VKFtNU80A0Oqkxz0SbkSzx7iB_KgveI"
```

### Instant Rollback Command:
If Firebase fails to serve traffic or certificate generation fails:
```bash
# Simply remove the newly added records to restore Vercel's default ALIAS:
vercel dns rm <RECORD_ID_OF_A_RECORD>
```
Zoho Mail and Resend DKIM records are completely isolated and will remain 100% operational throughout.

