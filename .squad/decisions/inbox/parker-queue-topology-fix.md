# Parker — Queue topology fix for ACA wiring

- **Date:** 2026-05-09
- **Issue:** #87
- **Author:** Parker

## Decision

Keep Service Bus queue topology explicitly split in IaC:

- `ingestionQueueName` = `extraccion-queue`
- `processingQueueName` = `extraccion-in`

## Why

The deployed ACA configuration had collapsed ingress and processing onto the same queue, bypassing the intended dedup handoff. The runtime design is a two-stage flow: upload-web publishes to ingress, dedup consumes ingress and forwards to processing, and orchestrator consumes only the processing queue.

## Implementation

- Updated `infra/modules/container-apps.bicep` to replace the single `extractionQueueName` input with `processingQueueName`.
- Wired Flow 0 dedup:
  - `FLOW0_SOURCE_QUEUE_NAME` → `ingestionQueueName`
  - `FLOW0_TARGET_QUEUE_NAME` → `processingQueueName`
- Wired orchestrator:
  - `SERVICEBUS_QUEUE_NAME` → `processingQueueName`
  - `EXTRACTION_QUEUE_NAME` → `processingQueueName`
  - KEDA Service Bus scaler `queueName` → `processingQueueName`
- Updated `infra/modules/main.bicep` to pass:
  - `ingestionQueueName` from `serviceBus.outputs.ingestionQueueName`
  - `processingQueueName` from `serviceBus.outputs.extraccionQueueName`

## Validation

- `az bicep build --file C:\repos\verdecoraSimpleTest\infra\modules\main.bicep` completed successfully.
