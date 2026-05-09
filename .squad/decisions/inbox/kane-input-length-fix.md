# Kane — Input length fix (Issue #98)

- **Date:** 2026-05-10
- **Decision:** Cap extractor input payloads at `MAX_EXTRACTION_INPUT_LENGTH = 15000` before sending OCR text to the Responses API.
- **Why:** Live OCR from `PRUEBA-1-4.pdf` exceeded the Responses API 16,384-character limit and triggered a 400 (`Invalid ''input[1].content'': array too long`). The SDK wrapped that failure as a `ChatClientException`, which surfaced as a generic extractor refusal.
- **Implementation:** `AlbaranPipeline._build_extraction_payload()` now truncates readable OCR text (or the document reference fallback), logs the original and truncated lengths, and returns the capped payload. Added a unit test to lock the behavior.
- **Follow-up:** If oversized OCR remains common, normalize Document Intelligence markdown/HTML tables into denser plain-text rows before truncation so we preserve more semantic content inside the same limit.
