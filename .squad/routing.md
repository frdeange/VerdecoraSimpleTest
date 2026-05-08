# Work Routing

How to decide who handles what.

## Routing Table

| Work Type | Route To | Examples |
|-----------|----------|----------|
| Architecture, simplification analysis, design decisions | Ripley | System design, ADR updates, component decisions, trade-offs |
| CI/CD, GitHub Actions, deployment pipelines, branch strategy | Dallas | Workflows, build-deploy pipelines, PR automation, release process |
| Bicep IaC, Azure resource modules, infra parameters | Parker | Bicep modules, resource provisioning, ARM deployments, infra simplification |
| Python code, FastAPI, services, Azure SDK integration | Kane | Application code, orchestrator, agents, config, service bus handlers |
| Frontend, upload-web, HTML/CSS/JS, UI components | Ash | Web forms, UI fixes, HITL webform, upload interface |
| Code review | Ripley | Review PRs, check quality, approve/reject |
| Testing, E2E, validation | Lambert | Write tests, find edge cases, verify deployments, E2E smoke tests |
| Scope & priorities | Ripley | What to build next, trade-offs, decisions |
| Session logging | Scribe | Automatic — never needs routing |

## Issue Routing

| Label | Action | Who |
|-------|--------|-----|
| `squad` | Triage: analyze issue, assign `squad:{member}` label | Ripley |
| `squad:ripley` | Architecture/design tasks | Ripley |
| `squad:dallas` | CI/CD, workflows, deployment | Dallas |
| `squad:parker` | Bicep, infrastructure | Parker |
| `squad:kane` | Backend code, services | Kane |
| `squad:ash` | Frontend, web UI | Ash |
| `squad:lambert` | Testing, validation | Lambert |

### How Issue Assignment Works

1. When a GitHub issue gets the `squad` label, **Ripley** triages it — analyzing content, assigning the right `squad:{member}` label, and commenting with triage notes.
2. When a `squad:{member}` label is applied, that member picks up the issue in their next session.
3. Members can reassign by removing their label and adding another member's label.
4. The `squad` label is the "inbox" — untriaged issues waiting for Ripley's review.

## Rules

1. **Eager by default** — spawn all agents who could usefully start work, including anticipatory downstream work.
2. **Scribe always runs** after substantial work, always as `mode: "background"`. Never blocks.
3. **Quick facts → coordinator answers directly.** Don't spawn an agent for "what port does the server run on?"
4. **When two agents could handle it**, pick the one whose domain is the primary concern.
5. **"Team, ..." → fan-out.** Spawn all relevant agents in parallel as `mode: "background"`.
6. **Anticipate downstream work.** If infra is being modified, spawn Lambert to prepare validation tests simultaneously.
7. **Issue-labeled work** — when a `squad:{member}` label is applied to an issue, route to that member. Ripley handles all `squad` (base label) triage.
