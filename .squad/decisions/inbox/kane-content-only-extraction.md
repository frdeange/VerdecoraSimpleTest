# Kane — Content-only extraction payload (Issue #104)

- **Date:** 2026-05-10
- **Decision:** The extractor path should send only Document Intelligence's `content` field to the Responses API.
- **Why:** Real ValidationTest output showed `content` alone is about 11,083 characters and already contains the full DI markdown representation needed by the LLM. Concatenating `key_value_pairs` and `tables` duplicated the same information, expanded the payload to roughly 19,657 characters, and exceeded the Responses API input limit.
- **Implementation:** Simplify `AlbaranPipeline._build_readable_ocr_text()` to normalize only `content`, remove `MAX_EXTRACTION_INPUT_LENGTH` truncation logic from `_build_extraction_payload()`, and have `OrchestratorService._build_pipeline_input()` pass through `content` directly as `raw_text`.
- **Preserved scope:** Keep the key/value and table formatting helpers in `pipeline.py` for possible future stages, but do not include them in extractor payload construction.
