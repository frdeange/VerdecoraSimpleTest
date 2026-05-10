# Kane — Extractor payload fix (Issue #98)

- **Date:** 2026-05-10
- **Decision:** The extractor stage must consume readable OCR text, not the raw Document Intelligence JSON payload.
- **Why:** The live model accepts plain OCR text locally, but the deployed pipeline was sending nested `ocr_payload` JSON (content + tables + key/value structures). That changed the effective prompt enough for the model to refuse with `"I'm sorry, but I cannot assist with that request"`, which then broke structured parsing.
- **Implementation:** `OrchestratorService._build_pipeline_input()` now populates `PipelineDocumentInput.raw_text` with formatted OCR text, and `AlbaranPipeline.run()` always uses readable text for extractor input. The formatter preserves the main OCR body plus human-readable key/value pairs and table summaries.
- **Fallback behavior:** If the extractor still returns a refusal or any non-JSON payload, log the actual model response preview and route the document to HITL instead of crashing the orchestration run.
