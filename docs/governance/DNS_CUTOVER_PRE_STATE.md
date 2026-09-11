# DTD Pre-Cutover DNS State Snapshot
**Captured:** 2026-09-11T10:00:18Z (UTC)  
**Captured by:** Antigravity agent, pre-DNS-cutover documentation requirement  
**Purpose:** Rollback reference — if Firebase DNS cutover fails, restore these exact records at the registrar / Vercel DNS panel.

---

## Current Nameservers (MUST CHANGE LAST)
```
dogtrainersdirectory.com.au.  21600 IN  NS  ns1.vercel-dns.com.
dogtrainersdirectory.com.au.  21600 IN  NS  ns2.vercel-dns.com.
```
**Registrar:** Nameservers are set at the domain registrar (not Vercel DNS). The Vercel DNS zone currently holds all other records below.

---

## A Records (Root domain — currently pointing to Vercel)
```
dogtrainersdirectory.com.au.  1800 IN  A  64.29.17.1
dogtrainersdirectory.com.au.  1800 IN  A  216.198.79.1
```
> These are Vercel's IPs. After cutover these become Firebase's IP: `199.36.158.100`

---

## CNAME (www — currently NO record)
```
(none — www CNAME is absent from current DNS)
```
> After cutover: `www CNAME gen-lang-client-0028123502.web.app.`

---

## MX Records — Zoho Mail (MUST BE PRESERVED EXACTLY)
```
dogtrainersdirectory.com.au.  3600 IN  MX  10  mx.zoho.com.
dogtrainersdirectory.com.au.  3600 IN  MX  20  mx2.zoho.com.
dogtrainersdirectory.com.au.  3600 IN  MX  50  mx3.zoho.com.
```
> ⚠️ These must be carried over unchanged to any new DNS zone. Loss of these = email outage.

---

## TXT Records — Zoho Verification + SPF (MUST BE PRESERVED EXACTLY)
```
dogtrainersdirectory.com.au.  60  IN  TXT  "zoho-verification=zb85165549.zmverify.zoho.com"
dogtrainersdirectory.com.au.  60  IN  TXT  "v=spf1 include:one.zoho.com ~all"
```

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

Since Vercel DNS is the authoritative zone, we can make all changes *within the existing Vercel DNS zone* by updating records via the Vercel CLI or dashboard:

1. Delete the two Vercel A records (`64.29.17.1`, `216.198.79.1`)
2. Add Firebase A record (`199.36.158.100`)
3. Add `www` CNAME
4. Add Firebase hosting TXT
5. Add 2× ACME challenge TXT records
6. Keep all Zoho MX + TXT records untouched

This requires zero nameserver change and no registrar involvement. TTL-based propagation only (~30 min for A records at TTL=1800).
