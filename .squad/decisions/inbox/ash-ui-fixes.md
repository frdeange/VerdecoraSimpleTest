# Ash — UI fixes for upload-web status consistency

- **Date:** 2026-05-10
- **Scope:** `src/upload_web/`
- **Decision:** Center the compact footer guidance card on the upload page and treat files without a started processing state as `queued` for display whenever the parent session is already `confirmed` or `processing`.
- **Why:** The guidance card regressed to left alignment after the upload layout rework, and the status page should not show a more advanced header state than every file row underneath it.
- **Impact:** Upload guidance is centered again, `/upload/{session_id}/status` shows “En cola” instead of “Pendiente” in the pre-processing gap, and the API status payload matches the UI display.
