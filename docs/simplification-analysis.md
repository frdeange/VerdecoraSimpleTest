# Verdecora Simple Simplification Analysis

**Author:** Ripley — Lead Architect  
**Generated:** 2026-05-08T13:30:11.303+02:00  
**Scope:** Simplify the current private-networked Azure design to public endpoints while preserving the MVP feature set.

---

## Executive summary

The current repository still reflects the enterprise-first topology from the original project: private VNet, private endpoints, NAT egress, self-hosted GitHub runners in Azure Container Apps Jobs, and Azure Front Door in front of the upload experience. That design is coherent, but it is too heavy for the current goal of shipping a simpler, operable system in `rg-verdecora-simple`.

The simplest viable target architecture is:

1. **Use public endpoints for all platform services**
2. **Keep managed identity + Entra ID + RBAC as the primary trust model**
3. **Move CI/CD to GitHub-hosted runners with Azure OIDC federation**
4. **Expose the upload web directly from Container Apps**
5. **Delete network-only infrastructure that no longer adds value**

This keeps the application architecture intact: FastAPI services, Container Apps, Cosmos DB, Service Bus, Blob Storage, Document Intelligence, Azure OpenAI/Foundry, ACS Email, and Easy Auth all remain. The main change is the **network boundary** and the **deployment model**, not the business flow.

---

## Part 1 — Current state analysis

### 1.1 Architecture documentation reviewed

Reviewed all files under `docs/architecture/`:

- `README.md`
- `orchestrator-spec.md`
- `agents-technical-spec.md`
- `data-models.md`
- `validation-inventory-spec.md`
- `post-mvp-agents.md`
- `prompt-engineering.md`
- `architecture-decision-record.md`

### 1.2 What the architecture says today

The architecture documents define a solid agentic MVP:

- Container Apps as the compute plane
- Service Bus for eventing and timers
- Cosmos DB as state/data-of-record
- Blob Storage for raw documents
- Document Intelligence / AI services for extraction and reasoning
- HITL via ACS Email + web form
- Managed identity and Azure-native integrations

However, the Architecture Decision Record also hard-locks several **private networking assumptions**:

- all infrastructure inside a private VNet
- private endpoints for core data-plane services
- self-hosted GitHub runners deployed inside ACA Jobs
- Front Door / protected edge assumptions around HITL and upload-web

That is the main tension in the repo today: **the product design is sound, but the hosting model is overbuilt for the current delivery goal**.

### 1.3 Current infrastructure shape

The current Bicep topology is centered in `infra/modules/main.bicep` and deploys a hardened stack that includes:

- resource group creation
- user-assigned identities and RBAC
- ACR
- Storage
- Service Bus
- Cosmos DB
- Key Vault
- Document Intelligence
- AI Foundry / Azure OpenAI wiring
- Event Grid
- monitoring and alerts
- Container Apps environment and apps/jobs
- dedicated upload-web ACA environment
- Easy Auth for upload-web
- VNet + subnets + NSGs
- NAT gateway
- private endpoints + private DNS zones
- Front Door + WAF
- self-hosted GitHub runners

### 1.4 Modules that currently enforce private-only operation

These modules are materially coupled to the private-network model:

| Module | Current behavior | Why it matters |
|---|---|---|
| `network.bicep` | Creates VNet, subnets, NSGs | Required only for private topology |
| `nat-gateway.bicep` | Dedicated outbound egress | Required only because workloads sit in private subnets |
| `private-endpoints.bicep` | Creates PE + private DNS for Storage/Cosmos/KV/SB/AI/DI | Core mechanism enabling private-only data-plane access |
| `container-apps.bicep` | Main ACA environment is VNet-integrated and internal | Prevents a simple public deployment |
| `upload-web-app.bicep` | Separate ACA env with subnet integration | Keeps upload-web tied to the VNet design |
| `frontdoor.bicep` | Front Door Premium + WAF + optional private link | Edge protection layer built for private origin |
| `runners.bicep` | Self-hosted GitHub runners in ACA Jobs | CI/CD depends on Azure-side runners |

These service modules are also configured for private-only or deny-by-default access and therefore must change if private networking is removed:

- `storage.bicep`
- `cosmos.bicep`
- `servicebus.bicep`
- `keyvault.bicep`
- `docintell.bicep`
- `ai-foundry.bicep`
- `monitoring.bicep`

### 1.5 Source code structure and dependency picture

The codebase is organized around a clear service split:

- `src/services/orchestrator/` — main orchestration service
- `src/services/flow0_dedup/` — early dedup/background processing
- `src/services/hitl_webform/` — human review web experience
- `src/services/escalation/` — timers/escalation flow
- `src/services/reconciliation/` — deferred capability
- `src/services/learning/` — deferred capability
- `src/upload_web/` — store/user upload application
- `src/shared/auth/` — shared Entra/Easy Auth support
- `src/agents/`, `src/models/`, `src/mcp/`, `src/config/` — agentic and integration support

Key observation: **application code is not deeply coupled to private DNS names or VNet-only hostnames**. Most integrations are endpoint + credential based, typically through managed identity or `DefaultAzureCredential`.

That is good news: simplification is mostly an **infrastructure and CI/CD refactor**, not a business-logic rewrite.

### 1.6 Upload-web specific findings

`src/upload_web/` is the most topology-sensitive part of the repo:

- it issues **user delegation SAS** for browser-to-blob uploads
- it stores upload session metadata in Cosmos
- it calls Document Intelligence during preflight/validation
- it relies on ACA Easy Auth headers and signed session handling
- it expects blob CORS to allow browser `PUT` requests from the public upload origin

This means:

- **Front Door removal affects CORS and allowed origins**
- **private Storage removal actually makes the current browser-upload model easier**
- `upload-web-auth.bicep` itself does **not** fundamentally require Front Door, but its audience/redirect assumptions must match the final public hostname

### 1.7 CI/CD current state

GitHub Actions currently use:

- `.github/workflows/build-deploy.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/upload-web-ci.yml`
- `.github/workflows/bicep-validate.yml`

Important current characteristics:

- `build-deploy.yml` runs on **`self-hosted`**
- Azure login uses **managed identity from the runner**
- builds are done with `az acr build`
- deployments update ACA apps/jobs directly
- resource names are hardcoded to `*-dev`
- resource group is hardcoded to `rg-verdecoratest-dev`

This is tightly coupled to `runners.bicep` and the current private Azure bootstrap path.

### 1.8 Docker/containerization current state

Dockerfiles reviewed:

- `docker/orchestrator/Dockerfile`
- `docker/hitl-webform/Dockerfile`
- `docker/flow0-dedup/Dockerfile`
- `docker/escalation-timer/Dockerfile`
- `docker/reconciliation/Dockerfile`
- `docker/learning/Dockerfile`
- `docker/upload-web/Dockerfile`
- `docker/github-runner/Dockerfile`

The service Dockerfiles are normal and survive the simplification unchanged. The one that becomes obsolete is:

- `docker/github-runner/Dockerfile`

### 1.9 Signals from the original repository

Relevant history in `frdeange/verdecoraTest` strongly confirms where complexity accumulated:

| Item | Relevance |
|---|---|
| Issue #171 / PR #172 | ACR was already simplified away from private endpoint/agent-pool complexity; this supports the current simplification direction |
| PR #178 / #181 / #182 | Upload-web auth, preflight, and edge behavior had repeated fixes around Front Door/origin handling |
| PR #187 | Upload-web ACA environment had to be recreated with VNet integration, showing fragility |
| PR #188 | Upload-web managed identity access needed repair after network changes |
| Issue #189 | Direct browser uploads to Blob broke under private-storage assumptions; backend-proxy upload was proposed as fallback |

Conclusion: the original repo shows a repeated pattern of **operational drag caused by network hardening**, especially around upload-web.

### 1.10 Baseline validation state

The current repo is not clean even before any simplification work:

- linting has pre-existing failures
- mypy has many pre-existing failures
- unit test collection currently breaks on `SequentialBuilder` imports
- some CI workflows tolerate failures with `|| true`

This does **not** block the simplification plan, but it matters for rollout sequencing: infrastructure simplification should be kept separate from unrelated code-health cleanup.

---

## Part 2 — Infrastructure simplification impact analysis

## 2.1 What gets removed and why

### Remove `infra/modules/network.bicep`

**What it does today**

- Creates VNet
- Creates subnets for ACA, private endpoints, upload-web, runners, etc.
- Applies NSG-driven segmentation

**Why remove it**

- Public-endpoint architecture no longer needs private subnet placement
- ACA managed environments can be public
- Service access shifts from private routing to public endpoints secured by identity/RBAC

**Impact**

- Removes subnet dependencies from Container Apps and upload-web
- Removes prerequisite for NAT and private endpoints
- Simplifies deployment order dramatically

### Remove `infra/modules/private-endpoints.bicep`

**What it does today**

- Creates private endpoints
- Creates private DNS zones and links
- Redirects service resolution to private IPs

**Why remove it**

- Public-endpoint strategy makes PE/DNS indirection unnecessary
- Private endpoints are the biggest source of operational coupling in the repo

**Impact**

- All affected services must explicitly allow public network access
- DNS becomes standard Azure public DNS again
- GitHub-hosted runners can reach Azure data-plane services without network bootstrap

### Remove `infra/modules/nat-gateway.bicep`

**What it does today**

- Provides deterministic egress for private-subnet workloads

**Why remove it**

- No private subnets = no need for NAT gateway

**Impact**

- Outbound IPs become platform-managed
- Any downstream IP allow-list strategy must be revisited

### Remove `infra/modules/runners.bicep`

**What it does today**

- Deploys self-hosted GitHub runners into Azure Container Apps Jobs
- Requires identities, secrets, image, and network reachability

**Why remove it**

- GitHub-hosted runners are the correct simplification move
- The runners are only needed because the platform was made private

**Impact**

- Azure deployment auth must move to GitHub OIDC federation
- `docker/github-runner/` becomes dead code
- identity/RBAC model must be simplified

### Remove `infra/modules/frontdoor.bicep`

**What it does today**

- Adds global edge routing
- Adds WAF
- Optionally bridges Front Door to private ACA origin

**Why remove it**

- Public upload-web can be exposed directly from ACA
- For the current scope, Front Door adds cost and deployment complexity without being required for business functionality

**Impact**

- Upload-web hostname changes
- Blob CORS origins must be updated
- WAF protections are lost and must be compensated for elsewhere

### Remove all references to the above in `main.bicep`

This is the key orchestration cleanup:

- remove `network` module deployment
- remove `nat-gateway` module deployment
- remove `private-endpoints` module deployment
- remove `runners` module deployment
- remove `frontdoor` module deployment
- remove `dependsOn` chains tied to those modules
- remove subnet ID plumbing
- simplify outputs to direct ACA/public service outputs

---

## 2.2 What gets modified and how

### Modify `infra/modules/main.bicep`

**Required change**

Turn `main.bicep` from a network-hardened composition root into a **public-endpoint composition root**.

**Specific changes**

- stop deploying network/NAT/PE/runners/Front Door
- stop passing subnet IDs into downstream modules
- remove network-hardening switches that no longer apply
- update resource-group naming to the simplified target
- update outputs to reference direct ACA FQDNs rather than Front Door outputs
- keep all business services and platform services in place

### Modify `infra/modules/container-apps.bicep`

**Required change**

Remove VNet integration and internal-only assumptions from the main ACA environment.

**Specific changes**

- remove `infrastructureSubnetId`
- remove managed environment `vnetConfiguration`
- set the environment up as a standard public ACA environment
- review whether orchestrator ingress should remain internal; if it is only event-driven, keep ingress disabled or tightly limited
- keep managed identity, secrets, scale rules, jobs, and ACR pull behavior intact

**Architectural note**

The simplification is about public Azure service endpoints, not about making every app internet-facing. Internal/event-driven apps can still remain non-public at the application level even without a custom VNet.

### Modify `infra/modules/upload-web-app.bicep`

**Required change**

Keep upload-web public, but remove subnet/VNet coupling.

**Specific changes**

- remove `infrastructureSubnetId`
- remove managed environment subnet settings
- keep external ingress enabled
- review environment variables that are built from naming conventions and ensure they remain correct without private DNS assumptions
- confirm blob/Cosmos/Service Bus/DI endpoints point to public endpoints

### Modify `infra/modules/identity.bicep`

**Required change**

Remove identities and RBAC assignments used only for the self-hosted runner pattern.

**Specific changes**

- remove runner-specific identity outputs/references
- keep runtime identities for ACA apps/jobs
- keep least-privilege RBAC for runtime workloads
- add a dedicated GitHub deployment principal/app registration in the delivery process rather than as a runner dependency

### Modify resource group naming

**Decision**

For the simplified repo, use **`rg-verdecora-simple`** as the primary target resource group name.

**Why**

- matches the explicit target given for this project
- simplest possible operating model
- avoids fake environment indirection while the repo is still converging

**Implication**

Replace current `rg-verdecoratest-${env}` references with `rg-verdecora-simple` unless a later multi-environment requirement is explicitly introduced.

### Modify parameter files under `infra/modules/parameters/`

**Required change**

Parameter files must stop carrying values that only make sense in the private topology.

**Specific changes**

- remove subnet-related parameters
- remove Front Door-related parameters
- remove runner/bootstrap-related parameters
- update CORS origins to the direct upload-web hostname or the final public custom domain
- align naming to `verdecora-simple` resources

---

## 2.3 Additional modules that must change even though they are not in the explicit removal list

These are essential to preserve functionality after private endpoints are deleted.

### `infra/modules/storage.bicep`

Change from private-only to public endpoint access with strong guardrails:

- enable public network access
- keep HTTPS only and minimum TLS
- keep blob public access disabled
- keep CORS tightly scoped to upload-web origin(s)
- keep user delegation SAS model

### `infra/modules/cosmos.bicep`

- enable public network access
- keep managed identity / Entra-based access
- review whether local auth can be disabled

### `infra/modules/servicebus.bicep`

- enable public network access
- prefer Entra auth over connection strings
- disable local/shared-key auth if the runtime does not need it

### `infra/modules/keyvault.bicep`

- enable public endpoint access or public firewall mode
- keep RBAC authorization
- avoid secret sprawl by keeping workloads on managed identity

### `infra/modules/docintell.bicep`

- enable public network access
- secure with Azure identity/key handling as required by the SDK path in use

### `infra/modules/ai-foundry.bicep`

- enable public network access
- keep model/version pinning
- prefer identity-based access wherever available

### `infra/modules/monitoring.bicep`

- review public ingestion/query flags
- ensure telemetry still flows without private networking
- keep RBAC and workspace-level controls

### `infra/README.md`

- remove stale reference to `enableUploadWebAppGateway`
- rewrite upload-web notes for the simplified public model

---

## 2.4 Impact on deployments

### GitHub Actions runner model

**Current**

- self-hosted ACA runners

**Target**

- GitHub-hosted runners (`ubuntu-latest`)

### What workflow files need updating

| Workflow | Action |
|---|---|
| `.github/workflows/build-deploy.yml` | Major redesign |
| `.github/workflows/bicep-validate.yml` | Update validation logic and temp-file handling |
| `.github/workflows/ci.yml` | Minor cleanup/alignment |
| `.github/workflows/upload-web-ci.yml` | Minor cleanup + upload-web config test coverage |

Squad/automation workflows do not appear topology-dependent and can remain unchanged.

### How GitHub Actions should authenticate to Azure

Use **GitHub OIDC federation** with `azure/login@v2`.

Recommended model:

- create one Entra application dedicated to GitHub deployments for this repo
- add federated credentials for the required branches/environments
- grant least-privilege RBAC:
  - resource-group-scoped contributor or a custom deployment role for infra
  - ACR push/build permissions
  - Container Apps update permissions if infra and app deployment remain separated

This removes the need for:

- self-hosted runner identity
- runner PAT storage in Key Vault
- runner bootstrap container

### Container image builds and pushes

Recommended simplest path:

- keep using `az acr build` from GitHub-hosted runners
- authenticate with OIDC
- push SHA-tagged and `latest` images as today

Why this is preferable:

- no Docker daemon complexity required on the runner
- no need to introduce a second build model during simplification
- ACR is already public-enabled in the repo

---

## 2.5 Impact on application code

### Service endpoints

No evidence was found that core services hardcode private-link hostnames. Most code uses standard service endpoints plus Azure identity. This means:

- **application code impact is low**
- **environment/config impact is moderate**

### Upload-web CORS changes

Front Door removal changes the browser origin that talks to Blob Storage.

What must happen:

- replace Front Door/custom-domain origins in Blob CORS with the final upload-web public origin
- ensure ACA direct hostname or chosen custom domain is the only allowed browser origin

### Upload-web auth flow

`upload-web-auth.bicep` does not fundamentally depend on Front Door, but these must be validated:

- redirect URIs
- allowed audiences
- post-login path behavior
- logout behavior

If they currently assume the Front Door host, they must be switched to the direct upload-web host or final custom domain.

### Direct browser upload vs backend-proxy upload

This is the key functional decision for upload-web.

**Recommendation:** keep the current **browser-to-Blob SAS upload** model for the simplified public design.

Why:

- it already exists
- it becomes viable again once Storage is public-accessible at the network layer
- it avoids adding backend upload load and complexity right now

Caveat:

Original repo Issue #189 proves that this model becomes fragile once Storage is forced private again. If the team ever reintroduces private Storage, backend-proxied uploads should be reconsidered.

---

## 2.6 Impact on security

### Security properties lost

Removing private networking loses several controls:

- no private-only data-plane reachability
- no subnet isolation between workloads and services
- no private DNS indirection
- no deterministic NAT egress identity
- no Front Door WAF in front of upload-web
- no Azure-hosted deployment enclave for CI/CD

### Security properties that remain

The design still retains strong Azure-native security if configured correctly:

- managed identity for runtime workloads
- Entra ID / Easy Auth for upload-web
- RBAC on Azure resources
- HTTPS/TLS enforcement
- service-level auth and authorization
- auditability through Azure control plane and app telemetry

### Recommended compensating controls

1. **Prefer identity over network trust**
   - managed identity for apps/jobs
   - OIDC federation for GitHub Actions
   - disable local/shared-key auth where services and SDK usage allow it

2. **Harden each public PaaS service**
   - public endpoint enabled, but no anonymous data access
   - RBAC only for Storage/Cosmos/Service Bus/Key Vault wherever feasible
   - keep public blob access disabled

3. **Harden upload-web at the app edge**
   - Easy Auth mandatory
   - Entra group allow-list
   - strict CORS
   - strict security headers
   - rate limiting / abuse protection in-app or via ACA-supported controls

4. **Keep secrets out of workflows**
   - no PAT-based runner bootstrap
   - no long-lived Azure credentials in GitHub secrets

5. **Restrict deployment permissions**
   - separate infra deployment role from runtime role if possible
   - scope GitHub deployment permissions to `rg-verdecora-simple`

6. **Preserve observability**
   - verify telemetry ingestion after public-endpoint shift
   - keep alerts, diagnostic settings, and audit logs

### Security conclusion

The simplified design is less isolated, but still acceptable for this project **if the trust model is intentionally shifted from network isolation to identity, RBAC, and service-level hardening**.

---

## Part 3 — Detailed action plan

## Phase 1 — Infrastructure cleanup (IaC)

### Files to delete

1. `infra/modules/network.bicep`
   - delete VNet/subnet/NSG topology
2. `infra/modules/private-endpoints.bicep`
   - delete all private endpoints and private DNS zones
3. `infra/modules/nat-gateway.bicep`
   - delete NAT-based egress
4. `infra/modules/runners.bicep`
   - delete self-hosted runner infrastructure
5. `infra/modules/frontdoor.bicep`
   - delete Front Door/WAF layer
6. `docker/github-runner/Dockerfile`
   - delete obsolete runner image

### Files to modify

7. `infra/modules/main.bicep`
   - remove deleted module references
   - remove subnet and dependency plumbing
   - switch RG naming to `rg-verdecora-simple`
   - output direct ACA/public endpoints

8. `infra/modules/container-apps.bicep`
   - remove `infrastructureSubnetId`
   - remove VNet config from managed environment
   - review ingress exposure service by service

9. `infra/modules/upload-web-app.bicep`
   - remove subnet integration
   - keep external ingress
   - align public endpoint env vars

10. `infra/modules/upload-web-auth.bicep`
    - align auth audience/redirect assumptions to the final public hostname

11. `infra/modules/identity.bicep`
    - remove runner identity outputs and RBAC
    - keep runtime identities only

12. `infra/modules/storage.bicep`
    - enable public network access
    - update CORS origins
    - keep blob access private/authenticated

13. `infra/modules/cosmos.bicep`
    - enable public network access
    - preserve MI/RBAC path

14. `infra/modules/servicebus.bicep`
    - enable public network access
    - preserve Entra auth path

15. `infra/modules/keyvault.bicep`
    - enable public endpoint access
    - preserve RBAC authorization

16. `infra/modules/docintell.bicep`
    - enable public network access

17. `infra/modules/ai-foundry.bicep`
    - enable public network access

18. `infra/modules/monitoring.bicep`
    - verify ingestion/query settings for the public model

19. `infra/modules/resource-group.bicep`
    - align default naming to `rg-verdecora-simple`

20. `infra/modules/parameters/dev.bicepparam`
    - remove private-topology parameters
    - align names and origins

21. `infra/modules/parameters/prod.bicepparam`
    - same cleanup if production remains in scope

22. `infra/README.md`
    - rewrite upload-web instructions for the simplified design
    - remove stale Application Gateway note

### Phase 1 acceptance criteria

- no Bicep module references remain to deleted network/runners/frontdoor modules
- all required PaaS services are reachable through public endpoints
- upload-web origin/CORS values are correct
- deployment can target `rg-verdecora-simple` without VNet prerequisites

---

## Phase 2 — CI/CD pipeline redesign

### Workflow files to modify

1. `.github/workflows/build-deploy.yml`
   - replace `runs-on: self-hosted` with `ubuntu-latest`
   - add `permissions: id-token: write, contents: read`
   - replace managed-identity runner login with OIDC-based `azure/login@v2`
   - replace hardcoded RG/name values with repo/environment variables
   - keep `az acr build`
   - keep `az containerapp update` / `az containerapp job update`
   - optionally split infra deploy from app deploy if desired

2. `.github/workflows/bicep-validate.yml`
   - stop using `/tmp/bicep_output.txt`
   - validate the simplified module graph
   - validate the active parameter files

3. `.github/workflows/ci.yml`
   - keep GitHub-hosted execution
   - align infra validation paths
   - plan a follow-up to remove false-green `|| true` behavior once baseline failures are fixed

4. `.github/workflows/upload-web-ci.yml`
   - keep GitHub-hosted execution
   - add tests/assertions around origin/auth config if introduced

### Workflow files to delete

- none required immediately, unless the team decides to replace `build-deploy.yml` with separate `deploy-infra.yml` and `deploy-services.yml`

### Azure authentication setup

1. Create a GitHub deployment Entra application
2. Add federated credentials for the repo/branch/environment
3. Store only non-secret identifiers in GitHub variables:
   - tenant ID
   - subscription ID
   - client ID
   - ACR name
   - resource group
4. Assign least-privilege RBAC at `rg-verdecora-simple`

### Phase 2 acceptance criteria

- no workflow depends on self-hosted runners
- GitHub Actions can log into Azure without stored secrets
- images build and deploy successfully from GitHub-hosted runners

---

## Phase 3 — Application code adjustments

### Files likely to need changes

1. `src/upload_web/config.py`
   - ensure public origin and service endpoint configuration stays explicit

2. `src/upload_web/routes/api.py`
   - confirm SAS upload flow still matches final Storage/CORS model

3. `src/upload_web/services/blob_sas.py`
   - verify no assumptions remain about private networking

4. `src/shared/auth/entra.py`
   - validate issuer/audience assumptions against final public hostname

5. `src/upload_web/middleware/session_security.py`
   - verify redirect/logout behavior against direct ACA host or chosen custom domain

6. `src/services/hitl_webform/config.py`
   - validate `public_base_url` and any public callback URLs if the edge hostname changes

### Files likely not to require logic changes

- orchestrator core service code
- Service Bus and Cosmos workflow code
- Dockerfiles for business services

### Phase 3 acceptance criteria

- upload-web login/upload/confirm flow works end to end
- no code references old Front Door hostnames
- no code depends on private DNS behavior

---

## Phase 4 — Deployment and validation

### Deployment steps

1. Create or confirm target resource group:
   - `rg-verdecora-simple`
2. Provision GitHub OIDC deployment identity and RBAC
3. Deploy simplified infrastructure via Bicep
4. Build and push images to ACR
5. Deploy/update ACA apps and jobs
6. Configure upload-web Easy Auth
7. Validate public origins and Blob CORS
8. Run end-to-end smoke tests

### E2E validation checklist

#### Platform validation

- Storage reachable from upload-web using managed identity/SAS flow
- Cosmos reachable from upload-web and services
- Service Bus reachable from services
- Key Vault reachable from ACA workloads
- Document Intelligence reachable from upload-web/service flows
- AI Foundry/OpenAI reachable from orchestrator flows

#### Upload-web validation

- login succeeds with Entra
- group-based authorization works
- file upload succeeds from the browser
- session record lands in Cosmos
- preflight/validation succeeds
- confirm/publish sends downstream message/event
- logout flow works

#### Service validation

- orchestrator app starts and is healthy
- dedup job can run successfully
- escalation timer job can run successfully
- hitl-webform public URL and callbacks work

#### Operational validation

- CI/CD pipeline completes from GitHub-hosted runners
- alerts/telemetry still arrive
- no residual dependency exists on private DNS, private endpoint approval, or runner bootstrap

---

## Phase 5 — DevOps best-practices setup

### Issue creation strategy

Create implementation issues by phase, not by layer confusion.

Recommended issue breakdown:

1. Delete private-network IaC modules
2. Convert PaaS modules to public-endpoint mode
3. Simplify ACA environments
4. Simplify upload-web topology and auth/cors config
5. Replace self-hosted runner deployment model with GitHub OIDC
6. Update deployment workflow
7. Validate end-to-end deployment into `rg-verdecora-simple`

### Branch protection

Recommended minimum:

- protect `master`
- require PRs
- require CI checks
- require at least one review
- block force-pushes
- require linear history or squash merge

### Recommended flow

1. create issue
2. create branch from issue
3. implement a narrow change set
4. run CI
5. open PR
6. review and merge
7. deploy via GitHub Actions
8. validate in Azure

This work should be executed as **small, reversible PRs**, not one large cutover.

---

## Recommended implementation order

1. **CI/CD authentication first**
   - establish GitHub OIDC and GitHub-hosted runner deployment path
2. **Delete runner dependency**
   - remove `runners.bicep` and `docker/github-runner`
3. **Delete network scaffolding**
   - remove VNet/NAT/PE/Front Door modules from the graph
4. **Open platform services safely**
   - update Storage/Cosmos/SB/KV/DI/AI modules
5. **Simplify ACA environments**
   - main services and upload-web
6. **Update upload-web hostname/CORS/auth**
7. **Deploy to `rg-verdecora-simple`**
8. **Run E2E validation**

This order minimizes the risk of ending up with a pipeline that can no longer deploy the target environment.

---

## Final architectural decisions for implementation

1. **Target resource group:** `rg-verdecora-simple`
2. **Runner model:** GitHub-hosted runners only
3. **Azure auth model for GitHub:** OIDC federation
4. **Upload-web exposure:** direct ACA public ingress
5. **Front Door:** removed for the simplified MVP
6. **Upload model:** keep direct browser-to-Blob SAS upload
7. **Security model:** shift from network isolation to identity + RBAC + service hardening
8. **Migration style:** small phased PRs, not a big-bang rewrite

---

## Bottom line

The simplification is feasible without changing the product architecture. The repo should be treated as an **infrastructure de-hardening and delivery-model simplification exercise**, not as an application redesign.

The highest-risk areas are:

- PaaS modules that are still configured as private-only
- upload-web CORS/auth hostname alignment after Front Door removal
- GitHub Actions authentication after runner removal

If those three areas are handled deliberately, the rest of the simplification is straightforward.
