# Squad Team

> Verdecora Simple — Simplified Azure deployment of the Verdecora Albaranes intelligent document processing system

## Coordinator

| Name | Role | Notes |
|------|------|-------|
| Squad | Coordinator | Routes work, enforces handoffs and reviewer gates. |

## Members

| Name | Role | Charter | Status |
|------|------|---------|--------|
| Ripley | Lead | `.squad/agents/ripley/charter.md` | 🏗️ Active |
| Dallas | DevOps | `.squad/agents/dallas/charter.md` | ⚙️ Active |
| Parker | IaC Expert | `.squad/agents/parker/charter.md` | 🔩 Active |
| Kane | Backend Dev | `.squad/agents/kane/charter.md` | 🔧 Active |
| Ash | Frontend Dev | `.squad/agents/ash/charter.md` | ⚛️ Active |
| Lambert | Tester | `.squad/agents/lambert/charter.md` | 🧪 Active |
| Scribe | Session Logger | `.squad/agents/scribe/charter.md` | 📋 Active |
| Ralph | Work Monitor | — | 🔄 Monitor |

## Project Context

- **User:** Kiko de Angel
- **Project:** Verdecora Simple — Albaranes ingestion, validation, and BC inventory automation
- **Stack:** Python 3.12, FastAPI, MAF SDK, Azure Container Apps, CosmosDB, Service Bus, Event Grid, Azure OpenAI, Document Intelligence, ACS Email, Business Central MCP
- **IaC:** Bicep (modules under `infra/`)
- **CI/CD:** GitHub Actions
- **Source repo (original complex):** https://github.com/frdeange/verdecoraTest
- **Target repo (simplified):** https://github.com/frdeange/VerdecoraSimpleTest
- **Azure Region:** Sweden Central
- **Target RG:** rg-verdecora-simple
- **Goal:** Simplify infrastructure by removing private networking (VNet, Private Endpoints, NAT Gateway, Front Door, self-hosted runners) while preserving all functional requirements
- **Created:** 2026-05-08

## Issue Source

- **Repository:** frdeange/VerdecoraSimpleTest
- **Connected:** 2026-05-08
