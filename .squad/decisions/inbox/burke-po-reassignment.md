# Burke — PO Reassignment & FANSA Test Data

**Date:** 2026-05-09  
**Author:** Burke (BC/Dynamics Specialist)  
**Requested by:** Kiko de Angel

---

## Task 1: PO 106031 Reassigned to V-HERSTERA ✅

### Result
**SUCCESS — vendor changed cleanly with no line disruption.**

| Field | Before | After |
|-------|--------|-------|
| Vendor No. | 10000 (Fabrikam, Inc.) | V-HERSTERA |
| Vendor Name | Fabrikam, Inc. | Herstera Garden S.L. |
| Pay-to Vendor | 10000 (Fabrikam, Inc.) | V-HERSTERA |
| Address | Atlanta, GA, US | Castellar del Vallès, Barcelona, ES |

### PO Details
- **PO Number:** 106031  
- **GUID:** `bf9251d9-c64b-f111-a820-002248b5dea4`  
- **Order Date:** 2021-04-10  
- **Lines:** 59 (all intact, no re-creation needed)  
- **Total:** $1,726.24  
- **Status:** Draft  

### Learnings
BC accepted the vendor change on a PO that already had 59 lines — no error. The `Modify_PurchaseOrder_PAG30066` action accepts `vendorId` + `vendorNumber` together and BC resolves address automatically from the vendor card. The `shortcutDimension1Code` was cleared (was "PURCHASING" under Fabrikam, now blank under V-HERSTERA) — not a problem for test purposes.

---

## Task 2: FANSA PO with Deliberate Discrepancies ✅

### Items Created in BC (13 total)

| Code | Description | BC Item GUID | Role |
|------|-------------|--------------|------|
| 8727WPZ | PLATO 27 WHITE G.(27,5 x 3,5) | f630627c-e24b-f111-a820-002248b5dea4 | In PO + albaran |
| 8727TPZ | PLATO CM.27 B.ROJO (27,5 x 3,5) | 3331627c-e24b-f111-a820-002248b5dea4 | In PO + albaran |
| 9EF60PZ | CILINDRO DAY R 45 CM. COTTO | 3231627c-e24b-f111-a820-002248b5dea4 | In PO + albaran |
| 9EF74PZ | CILINDRO DAY R 50 CM. ANTRACI. | bbf98483-e24b-f111-a820-002248b5dea4 | In PO + albaran |
| 9EH30PZ | PLATO CIRC.DAY R 30 CM. COTTO | baf98483-e24b-f111-a820-002248b5dea4 | In PO + albaran |
| 9EM10PZ | PLATO JARD.DAY R 40 CM. COTTO | bcf98483-e24b-f111-a820-002248b5dea4 | In PO + albaran |
| 9EM14PZ | PLATO JARD.DAY R 40 CM. ANTRA. | bef98483-e24b-f111-a820-002248b5dea4 | In PO + albaran |
| 9EM20PZ | PLATO JARD.DAY R 50 CM. COTTO | bdf98483-e24b-f111-a820-002248b5dea4 | In PO + albaran |
| 9EM24PZ | PLATO JARD.DAY R 50 CM. ANTRA. | 01a9248f-e24b-f111-a820-002248b5dea4 | In albaran, **OMITTED from PO** |
| 063108Z | TERRINA GRANDE 31 B.ROJO | 00a9248f-e24b-f111-a820-002248b5dea4 | In PO + albaran |
| 065108Z | TERRINA GRANDE 61 B.ROJO | ffa8248f-e24b-f111-a820-002248b5dea4 | In albaran, **OMITTED from PO** |
| GHOST-001 | GHOST ITEM 001 (E2E test - not in albaran) | 02a9248f-e24b-f111-a820-002248b5dea4 | **In PO only — ghost** |
| GHOST-002 | GHOST ITEM 002 (E2E test - not in albaran) | fea8248f-e24b-f111-a820-002248b5dea4 | **In PO only — ghost** |

All items created with `generalProductPostingGroupCode: "RETAIL"` and `inventoryPostingGroupCode: "RESALE"`.

---

### FANSA PO Details

- **PO Number:** 106032  
- **GUID:** `a4d08f95-e24b-f111-a820-002248b5dea4`  
- **Vendor:** V-FANSA — FANSA Fabricación Alfarera Navarrete S.A.U. (`005811b2-e04b-f111-a820-002248b5dea4`)  
- **Order Date:** 2021-04-18 (2 days before albaran date 2021-04-20)  
- **Status:** Draft  
- **Lines:** 11  

---

### Discrepancy Map (What the Pipeline Should Detect)

| Item Code | Description | PO Qty | Albaran Qty | Discrepancy Type | Delta |
|-----------|-------------|--------|-------------|-----------------|-------|
| **8727WPZ** | PLATO 27 WHITE G. | **20** | 12 | ⚠️ Quantity mismatch (PO > albaran) | +8 |
| **8727TPZ** | PLATO CM.27 B.ROJO | **6** | 12 | ⚠️ Quantity mismatch (PO < albaran) | −6 |
| **9EF60PZ** | CILINDRO DAY R 45 CM. COTTO | **15** | 10 | ⚠️ Quantity mismatch (PO > albaran) | +5 |
| 9EF74PZ | CILINDRO DAY R 50 CM. ANTRACI. | 5 | 5 | ✅ Match | 0 |
| 9EH30PZ | PLATO CIRC.DAY R 30 CM. COTTO | 25 | 25 | ✅ Match | 0 |
| 9EM10PZ | PLATO JARD.DAY R 40 CM. COTTO | 10 | 10 | ✅ Match | 0 |
| 9EM14PZ | PLATO JARD.DAY R 40 CM. ANTRA. | 10 | 10 | ✅ Match | 0 |
| 9EM20PZ | PLATO JARD.DAY R 50 CM. COTTO | 10 | 10 | ✅ Match | 0 |
| **9EM24PZ** | PLATO JARD.DAY R 50 CM. ANTRA. | **—** | 10 | ❌ Albaran item missing from PO | N/A |
| 063108Z | TERRINA GRANDE 31 B.ROJO | 24 | 24 | ✅ Match | 0 |
| **065108Z** | TERRINA GRANDE 61 B.ROJO | **—** | 6 | ❌ Albaran item missing from PO | N/A |
| **GHOST-001** | GHOST ITEM 001 | **5** | — | 👻 PO item not in albaran | N/A |
| **GHOST-002** | GHOST ITEM 002 | **8** | — | 👻 PO item not in albaran | N/A |

### Summary of Expected Discrepancy Detections
- **3 quantity mismatches:** 8727WPZ (+8), 8727TPZ (−6), 9EF60PZ (+5)
- **2 items in albaran but NOT in PO:** 9EM24PZ, 065108Z → pipeline should flag as "unexpected delivery"
- **2 ghost items in PO but NOT in albaran:** GHOST-001, GHOST-002 → pipeline should flag as "ordered item not delivered"
- **Total discrepancy triggers:** 7 — should force HITL routing

### Albaran Reference
- Albaran: PRUEBA-5.pdf (FANSA, Nº 3499, Fecha 20/04/2021)
- PO order date is 2021-04-18 (2 days before albaran) — chronologically correct

---

## Next Steps

1. Run PRUEBA-5.pdf through the pipeline against PO 106032
2. Verify HITL routing triggers on the 7 discrepancy points
3. Once FANSA scenario passes E2E, PO 106031 (now under V-HERSTERA) is ready for PRUEBA-1-4.pdf clean-match scenario
