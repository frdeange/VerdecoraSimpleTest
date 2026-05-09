/**
 * Verdecora Upload Web — Client-side upload via SAS tokens
 *
 * Flow:
 *  1. User drops/selects files in the dropzone
 *  2. For each file: POST /api/sessions/{id}/sas → get SAS URL
 *  3. PUT file to SAS URL directly (browser → Azure Blob Storage)
 *  4. On success: POST /api/sessions/{id}/files → register metadata
 *  5. Update file list via HTMX swap
 */

(function () {
  "use strict";

  const ACCEPTED_TYPES = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/tiff",
  ];
  const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB
  const UPLOAD_STATE_PENDING = "pending";
  const UPLOAD_STATE_UPLOADING = "uploading";
  const UPLOAD_STATE_COMPLETE = "complete";
  const UPLOAD_STATE_ERROR = "error";
  const STEP_FILES = 1;
  const STEP_ANALYSIS = 2;
  const STEP_CONFIRM = 3;

  /**
   * Return CSRF token from <meta> tag.
   */
  function getCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.content : "";
  }

  /**
   * Format bytes to a human-readable string.
   */
  function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  /**
   * Validate a file before upload.
   */
  function validateFile(file) {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      return "Tipo de archivo no permitido. Usa PDF, JPG, PNG o TIFF.";
    }
    if (file.size > MAX_FILE_SIZE) {
      return "El archivo supera el límite de 50 MB.";
    }
    return null;
  }

  /**
   * Create a file item element for the upload list.
   */
  function createFileItemEl(file, tempId) {
    const div = document.createElement("div");
    div.className = "file-item";
    div.dataset.tempId = tempId;
    div.dataset.uploadState = UPLOAD_STATE_PENDING;
    div.draggable = false;

    const isImage = file.type.startsWith("image/");
    let iconHtml;
    if (isImage) {
      iconHtml =
        '<img class="file-thumb" src="' +
        URL.createObjectURL(file) +
        '" alt="">';
    } else {
      iconHtml = '<span class="file-icon">📄</span>';
    }

    div.innerHTML =
      iconHtml +
      '<span class="file-name">' +
      file.name +
      "</span>" +
      '<span class="file-size">' +
      formatSize(file.size) +
      "</span>" +
      '<div class="file-progress"><div class="file-progress-bar" style="width:0%"></div></div>' +
      '<button type="button" class="file-remove" title="Quitar archivo">✕</button>';

    div.querySelector(".file-remove").addEventListener("click", function () {
      div.remove();
      updateFileCount();
    });

    return div;
  }

  function bindDragStart(item) {
    if (item.dataset.dragBound === "true") {
      return;
    }
    item.addEventListener("dragstart", function (e) {
      e.dataTransfer.setData("text/plain", item.dataset.fileId);
    });
    item.dataset.dragBound = "true";
  }

  function getStepElements() {
    return Array.from(document.querySelectorAll("#upload-stepper .step[data-step]"));
  }

  function setActiveStep(stepNumber) {
    getStepElements().forEach(function (step) {
      const currentStep = Number(step.dataset.step || "0");
      step.classList.remove("active", "completed");

      if (currentStep < stepNumber) {
        step.classList.add("completed");
      } else if (currentStep === stepNumber) {
        step.classList.add("active");
      }
    });
  }

  function setButtonLoading(button, isLoading) {
    if (!button) return;

    if (isLoading) {
      button.dataset.wasDisabled = button.disabled ? "true" : "false";
      button.disabled = true;
    } else {
      button.disabled = button.dataset.wasDisabled === "true";
      delete button.dataset.wasDisabled;
    }

    button.classList.toggle("is-loading", isLoading);
    button.setAttribute("aria-busy", isLoading ? "true" : "false");
  }

  function setInlineLoading(isLoading, message) {
    const loadingEl = document.getElementById("preflight-loading");
    if (!loadingEl) return;

    loadingEl.style.display = isLoading ? "inline-flex" : "none";
    if (message) {
      loadingEl.innerHTML = '<span class="spinner"></span>&nbsp;' + message;
    }
  }

  function getConfidenceTone(confidence) {
    if (confidence > 0.7) return "success";
    if (confidence >= 0.3) return "warning";
    return "error";
  }

  function getConfidenceBadgeClass(confidence) {
    if (confidence > 0.7) return "confidence-high";
    if (confidence >= 0.3) return "confidence-medium";
    return "confidence-low";
  }

  function createElement(tagName, className, text) {
    const el = document.createElement(tagName);
    if (className) {
      el.className = className;
    }
    if (typeof text === "string") {
      el.textContent = text;
    }
    return el;
  }

  function createResultField(label, value) {
    const field = createElement("div", "preflight-results-field");
    const dt = createElement("dt", "preflight-results-label", label);
    const dd = createElement("dd", "preflight-results-value", value);
    field.appendChild(dt);
    field.appendChild(dd);
    return field;
  }

  function renderWarnings(warnings) {
    if (!warnings || warnings.length === 0) {
      return null;
    }

    const warningBox = createElement("div", "preflight-warning-box");
    const title = createElement("p", "preflight-warning-title", "Avisos detectados");
    const list = createElement("ul", "preflight-warning-list");

    warnings.forEach(function (warning) {
      const item = createElement("li", "preflight-warning-item", warning);
      list.appendChild(item);
    });

    warningBox.appendChild(title);
    warningBox.appendChild(list);
    return warningBox;
  }

  function setPreflightPanelState(showResults) {
    const instructionsEl = document.getElementById("preflight-instructions");
    const resultsEl = document.getElementById("preflight-results");

    if (instructionsEl) {
      instructionsEl.hidden = showResults;
    }

    if (resultsEl) {
      resultsEl.hidden = !showResults;
    }
  }

  function renderMessageCard(message, tone) {
    const resultsEl = document.getElementById("preflight-results");
    if (!resultsEl) return;

    setPreflightPanelState(true);
    resultsEl.innerHTML = "";

    const card = createElement("section", "preflight-results-card result-card " + tone);
    const body = createElement("p", "preflight-message", message);
    card.appendChild(body);
    resultsEl.appendChild(card);
  }

  async function confirmSession(confirmButton, confirmUrl, statusUrl) {
    const resultsEl = document.getElementById("preflight-results");
    const preflightButton = document.getElementById("btn-next-preflight");

    try {
      setActiveStep(STEP_CONFIRM);
      setButtonLoading(confirmButton, true);
      if (preflightButton) {
        preflightButton.disabled = true;
      }

      const resp = await fetch(confirmUrl, {
        method: "POST",
        headers: {
          "X-CSRF-Token": getCsrfToken(),
        },
      });

      if (!resp.ok) {
        let message = "No se pudo confirmar el albarán.";
        try {
          const errorBody = await resp.json();
          if (errorBody && errorBody.detail) {
            message = errorBody.detail;
          }
        } catch (error) {
          console.warn("Could not parse confirm error response.", error);
        }
        throw new Error(message);
      }

      if (statusUrl) {
        window.location.assign(statusUrl);
      }
    } catch (error) {
      if (resultsEl) {
        const existingError = resultsEl.querySelector(".preflight-inline-error");
        if (existingError) {
          existingError.remove();
        }
        const errorMessage = createElement(
          "p",
          "preflight-inline-error",
          error.message || "No se pudo confirmar el albarán."
        );
        resultsEl.appendChild(errorMessage);
      }
      setActiveStep(STEP_ANALYSIS);
      if (preflightButton) {
        updateFileCount();
      }
    } finally {
      setButtonLoading(confirmButton, false);
    }
  }

  function renderPreflightResults(result, options) {
    const resultsEl = document.getElementById("preflight-results");
    if (!resultsEl) return;

    const confidence = Number(result.confidence || 0);
    const tone = getConfidenceTone(confidence);
    const card = createElement("section", "preflight-results-card result-card " + tone);
    const header = createElement("div", "preflight-results-header");
    const titleBlock = createElement("div", "preflight-results-heading");
    const eyebrow = createElement("p", "preflight-results-eyebrow", "Resultado del análisis");
    const title = createElement(
      "h2",
      "preflight-results-title",
      result.is_albaran ? "✅ Es albarán" : "⚠️ Revisar documento"
    );
    const confidenceBadge = createElement(
      "span",
      "confidence-badge " + getConfidenceBadgeClass(confidence),
      "Confianza " + Math.round(confidence * 100) + "%"
    );
    const details = createElement("dl", "preflight-results-grid");
    const actions = createElement("div", "preflight-results-actions");
    const confirmButton = createElement("button", "btn-primary", "Siguiente: Confirmar →");

    titleBlock.appendChild(eyebrow);
    titleBlock.appendChild(title);
    header.appendChild(titleBlock);
    header.appendChild(confidenceBadge);

    details.appendChild(
      createResultField("Proveedor", result.detected_supplier || "No detectado")
    );
    details.appendChild(
      createResultField("Fecha", result.detected_date || "No detectada")
    );
    details.appendChild(
      createResultField(
        "Nº Albarán",
        result.detected_albaran_number || "No detectado"
      )
    );
    details.appendChild(
      createResultField("Tienda", result.detected_store || "No detectada")
    );

    confirmButton.type = "button";
    confirmButton.addEventListener("click", function () {
      confirmSession(confirmButton, options.confirmUrl, options.statusUrl);
    });
    actions.appendChild(confirmButton);

    card.appendChild(header);
    card.appendChild(details);

    const warnings = renderWarnings(result.warnings || []);
    if (warnings) {
      card.appendChild(warnings);
    }

    card.appendChild(actions);

    setPreflightPanelState(true);
    resultsEl.innerHTML = "";
    resultsEl.appendChild(card);
    setActiveStep(STEP_ANALYSIS);
    resultsEl.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  /**
   * Update the visible file count badge.
   */
  function updateFileCount() {
    const list = document.getElementById("file-list");
    const counter = document.getElementById("file-count");
    const nextBtn = document.getElementById("btn-next-preflight");
    if (!list) return;

    const items = Array.from(list.querySelectorAll(".file-item"));
    const count = items.length;
    const completedCount = items.filter(function (item) {
      return item.dataset.uploadState === UPLOAD_STATE_COMPLETE;
    }).length;
    const pendingUploads = items.filter(function (item) {
      return (
        item.dataset.uploadState === UPLOAD_STATE_PENDING ||
        item.dataset.uploadState === UPLOAD_STATE_UPLOADING
      );
    }).length;

    if (counter) {
      if (count === 0) {
        counter.textContent = "";
      } else if (pendingUploads > 0) {
        counter.textContent =
          completedCount +
          "/" +
          count +
          " archivo(s) listos · " +
          pendingUploads +
          " subiendo…";
      } else {
        counter.textContent = completedCount + " archivo(s) listos para analizar";
      }
    }
    if (nextBtn) {
      nextBtn.disabled = completedCount === 0 || pendingUploads > 0;
    }
  }

  /**
   * Request a SAS token for one file.
   */
  async function requestSas(sessionId, filename, contentType) {
    const params = new URLSearchParams({ filename: filename });
    const resp = await fetch("/api/sessions/" + sessionId + "/sas?" + params.toString(), {
      method: "POST",
      headers: {
        "X-CSRF-Token": getCsrfToken(),
      },
    });
    if (!resp.ok) {
      throw new Error("No se pudo obtener la URL de subida (SAS).");
    }
    const body = await resp.json();
    if (!(body.upload_url || body.sas_url) || !body.blob_path) {
      throw new Error("La respuesta SAS no incluye la URL o la ruta del blob.");
    }
    return {
      uploadUrl: body.upload_url || body.sas_url || "",
      blobPath: body.blob_path || "",
    };
  }

  /**
   * Upload a file directly to Azure Blob Storage via SAS URL.
   */
  async function uploadToBlob(sasUrl, file, progressBar) {
    return new Promise(function (resolve, reject) {
      const xhr = new XMLHttpRequest();
      xhr.open("PUT", sasUrl, true);
      xhr.setRequestHeader("x-ms-blob-type", "BlockBlob");
      xhr.setRequestHeader("Content-Type", file.type);

      xhr.upload.addEventListener("progress", function (e) {
        if (e.lengthComputable && progressBar) {
          const pct = Math.round((e.loaded / e.total) * 100);
          progressBar.style.width = pct + "%";
        }
      });

      xhr.addEventListener("load", function () {
        if (xhr.status >= 200 && xhr.status < 300) {
          if (progressBar) {
            progressBar.style.width = "100%";
            progressBar.classList.add("complete");
          }
          resolve();
        } else {
          reject(new Error("Error al subir a almacenamiento: " + xhr.status));
        }
      });

      xhr.addEventListener("error", function () {
        reject(new Error("Error de red al subir el archivo."));
      });

      xhr.send(file);
    });
  }

  /**
   * Register uploaded file metadata with the backend.
   */
  async function registerFile(sessionId, filename, blobPath, contentType, size) {
    const resp = await fetch("/api/sessions/" + sessionId + "/files", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": getCsrfToken(),
      },
      body: JSON.stringify({
        filename: filename,
        blob_path: blobPath,
        mime_type: contentType,
        size_bytes: size,
      }),
    });
    if (!resp.ok) {
      throw new Error("No se pudo registrar el archivo.");
    }
    return resp.json();
  }

  /**
   * Process a single file: SAS → Blob upload → register.
   */
  async function processFile(sessionId, file, fileItemEl) {
    const progressBar = fileItemEl.querySelector(".file-progress-bar");
    fileItemEl.dataset.uploadState = UPLOAD_STATE_UPLOADING;
    updateFileCount();
    try {
      const sas = await requestSas(sessionId, file.name, file.type);
      await uploadToBlob(sas.uploadUrl, file, progressBar);
      const registration = await registerFile(
        sessionId,
        file.name,
        sas.blobPath,
        file.type,
        file.size
      );
      fileItemEl.dataset.uploadState = UPLOAD_STATE_COMPLETE;
      fileItemEl.dataset.fileId = registration.file_id || fileItemEl.dataset.tempId;
      fileItemEl.draggable = true;
      bindDragStart(fileItemEl);
      updateFileCount();
    } catch (err) {
      if (progressBar) {
        progressBar.classList.add("error");
      }
      fileItemEl.dataset.uploadState = UPLOAD_STATE_ERROR;
      updateFileCount();
      console.error("Upload failed for " + file.name + ":", err);
      throw err;
    }
  }

  /**
   * Handle file selection (from input or drop).
   */
  function handleFiles(files, sessionId) {
    const list = document.getElementById("file-list");
    if (!list) return;

    const emptyState = list.querySelector(".empty-state");
    if (emptyState) {
      emptyState.remove();
    }

    Array.from(files).forEach(function (file, idx) {
      const error = validateFile(file);
      if (error) {
        alert(file.name + ": " + error);
        return;
      }

      const tempId = "temp-" + Date.now() + "-" + idx;
      const el = createFileItemEl(file, tempId);
      list.appendChild(el);

      if (sessionId) {
        processFile(sessionId, file, el).catch(function () {
          // error already logged; keep UI item to show error state
        });
      }
    });

    updateFileCount();
  }

  /**
   * Initialize dropzone interactions.
   */
  function initDropzone() {
    const dropzone = document.getElementById("dropzone");
    if (!dropzone) return;

    const fileInput = dropzone.querySelector('input[type="file"]');
    const sessionId = dropzone.dataset.sessionId || "";

    if (!sessionId) {
      console.error("Upload session is missing; the upload page must create a session before file selection.");
      return;
    }

    dropzone.addEventListener("dragover", function (e) {
      e.preventDefault();
      dropzone.classList.add("dragover");
    });

    dropzone.addEventListener("dragleave", function () {
      dropzone.classList.remove("dragover");
    });

    dropzone.addEventListener("drop", function (e) {
      e.preventDefault();
      dropzone.classList.remove("dragover");
      if (e.dataTransfer && e.dataTransfer.files.length > 0) {
        handleFiles(e.dataTransfer.files, sessionId);
      }
    });

    if (fileInput) {
      fileInput.addEventListener("change", function () {
        handleFiles(fileInput.files, sessionId);
        fileInput.value = "";
      });
    }

    // "Add more files" button
    var addBtn = document.getElementById("btn-add-files");
    if (addBtn && fileInput) {
      addBtn.addEventListener("click", function () {
        fileInput.click();
      });
    }
  }

  /**
   * Initialize page grouping drag-and-drop.
   */
  function initGrouping() {
    document.querySelectorAll(".albaran-group").forEach(function (group) {
      group.addEventListener("dragover", function (e) {
        e.preventDefault();
        group.classList.add("drag-over");
      });

      group.addEventListener("dragleave", function () {
        group.classList.remove("drag-over");
      });

      group.addEventListener("drop", function (e) {
        e.preventDefault();
        group.classList.remove("drag-over");
        var fileId = e.dataTransfer.getData("text/plain");
        var item = document.querySelector('[data-file-id="' + fileId + '"]');
        if (item) {
          group.querySelector(".albaran-group-files").appendChild(item);
        }
      });
    });

    document.querySelectorAll(".file-item[draggable='true']").forEach(function (item) {
      bindDragStart(item);
    });
  }

  function initPreflightFlow() {
    const button = document.getElementById("btn-next-preflight");
    if (!button || button.dataset.bound === "true") {
      return;
    }

    const preflightUrl = button.dataset.preflightUrl || "";
    const confirmUrl = button.dataset.confirmUrl || "";
    const statusUrl = button.dataset.statusUrl || "";

    button.addEventListener("click", async function () {
      if (!preflightUrl || button.disabled) {
        return;
      }

      try {
        setButtonLoading(button, true);
        setInlineLoading(true, "Preparando análisis…");

        const resp = await fetch(preflightUrl, {
          method: "POST",
          headers: {
            "X-CSRF-Token": getCsrfToken(),
          },
        });

        if (!resp.ok) {
          let message = "No se pudo completar el análisis.";
          try {
            const errorBody = await resp.json();
            if (errorBody && errorBody.detail) {
              message = errorBody.detail;
            }
          } catch (error) {
            console.warn("Could not parse preflight error response.", error);
          }
          throw new Error(message);
        }

        const result = await resp.json();
        renderPreflightResults(result, {
          confirmUrl: confirmUrl,
          statusUrl: statusUrl,
        });
      } catch (error) {
        renderMessageCard(
          error.message || "No se pudo completar el análisis.",
          "error"
        );
      } finally {
        setButtonLoading(button, false);
        setInlineLoading(false);
        updateFileCount();
      }
    });

    button.dataset.bound = "true";
  }

  // Boot
  document.addEventListener("DOMContentLoaded", function () {
    initDropzone();
    initGrouping();
    initPreflightFlow();
    setPreflightPanelState(false);
    setActiveStep(STEP_FILES);
  });

  // Re-init after HTMX swaps
  document.addEventListener("htmx:afterSwap", function () {
    initGrouping();
    updateFileCount();
  });
})();
