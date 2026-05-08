# Scripts

## `setup-github-oidc.ps1`

Bootstraps GitHub Actions OIDC for an Azure deployment repository.

What it does:

- validates Azure CLI and GitHub CLI prerequisites
- discovers the active subscription and the ACR in the target resource group
- creates or reuses an Entra app registration and service principal
- creates federated credentials for `master` and `pull_request`
- assigns `Contributor` on the subscription and `AcrPush` on the ACR
- sets the required GitHub repository variables

### Example

```powershell
./scripts/setup-github-oidc.ps1 -GitHubOrg frdeange -GitHubRepo VerdecoraSimpleTest -ResourceGroup rg-verdecora-simple-dev
```

### Parameters

- `GitHubOrg` — GitHub owner or organization
- `GitHubRepo` — GitHub repository name
- `ResourceGroup` — Azure resource group used to discover the deployment target and ACR
- `AppName` — optional Entra app registration display name
- `Environment` — optional environment label used for the `ENVIRONMENT` GitHub variable
