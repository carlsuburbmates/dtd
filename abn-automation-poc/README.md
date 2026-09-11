# DTD Automated ABN & Entity Verification Pipeline (Standalone POC)

This isolated proof-of-concept tests and verifies the complete **Australian Business Number (ABN) Verification & Entity Lifecycle Pipeline** without modifying any core DTD application code.

---

## 1. Directory Structure

```
abn-automation-poc/
├── abn_validator.py        # ATO Modulus 89 Checksum Algorithm (0ms offline validation)
├── abr_client.py           # Official ABR Web Services Client (with 30-day cache & live/mock modes)
├── deduplication.py        # Entity matching & deduplication engine (ABN, Phone, Domain)
├── verification_engine.py  # Automated trust badge provisioning & 14-day re-verification lifecycle
├── test_data.json          # Test dataset (Valid VIC ABNs, fake ABNs, cancelled ABNs, duplicates)
├── test_pipeline_e2e.py    # 10 comprehensive E2E unit and integration tests
├── run_demo.py             # CLI runner with formatted terminal output
└── README.md               # Documentation
```

---

## 2. How to Run the Test Suite

### Option A: Run the E2E Test Suite
```bash
python3 abn-automation-poc/test_pipeline_e2e.py
```
*(Executes all 10 unit and integration tests covering checksums, ABR lookups, deduplication mergers, delisting suppression, and badge revocations).*

### Option B: Run with Mock Data (Offline / Isolated)
```bash
python3 abn-automation-poc/run_demo.py
```

### Option C: Run with Live ABR Web Services GUID
```bash
python3 abn-automation-poc/run_demo.py --guid YOUR_ABR_GUID
```
*(Directly queries live Australian Government ABR servers via `https://abr.business.gov.au/json/AbnDetails.aspx` and caches results to `cache/abr_cache.json`).*

---

## 3. Verified Pipelines

1. **Stage 1 (Checksum)**: 11-digit format validation and ATO Modulus 89 checksum ($(\sum d_i 	imes w_i) \pmod{89} == 0$).
2. **Stage 2 (ABR Lookup)**: Extracts legal entity name, trading business names, active status, state/postcode, and GST registration status.
3. **Stage 3 (Deduplication)**: Merges incoming multi-source listings on canonical ABN or normalized phone/domain without duplicate profile creation.
4. **Stage 4 (Badge Activation)**: Automatically provisions the *"✓ ABN Verified • Registered Australian Business"* trust badge and metadata popover.
5. **Stage 5 (Lifecycle Monitoring)**: Simulates 14-day periodic re-verification to detect business cancellations and revoke badges automatically.
