[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$GitHubOrg,

    [Parameter(Mandatory = $true)]
    [string]$GitHubRepo,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory = $false)]
    [string]$AppName = "github-deploy-$GitHubRepo",

    [Parameter(Mandatory = $false)]
    [string]$Environment = "dev"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Small helpers keep CLI execution and error handling consistent.
function Test-CommandAvailable {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    return $null -ne (Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

function Invoke-AzJson {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    $output = & az @Arguments --output json 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage`n$output"
    }

    if ([string]::IsNullOrWhiteSpace(($output | Out-String))) {
        return $null
    }

    return $output | ConvertFrom-Json
}

function Invoke-Az {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    $output = & az @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage`n$output"
    }

    return $output
}

function Invoke-Gh {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,

        [Parameter(Mandatory = $true)]
        [string]$FailureMessage
    )

    $output = & gh @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "$FailureMessage`n$output"
    }

    return $output
}

function Ensure-FederatedCredential {
    param(
        [Parameter(Mandatory = $true)]
        [string]$AppObjectId,

        [Parameter(Mandatory = $true)]
        [hashtable]$Definition
    )

    # Federated credentials are keyed by name, so we can safely reuse them when present.
    $existingCredentials = Invoke-AzJson -Arguments @(
        "ad", "app", "federated-credential", "list",
        "--id", $AppObjectId
    ) -FailureMessage "Failed to list federated credentials for app object id '$AppObjectId'."

    $existing = @($existingCredentials | Where-Object { $_.name -eq $Definition.name }) | Select-Object -First 1
    if ($null -ne $existing) {
        return [PSCustomObject]@{
            Name    = $Definition.name
            Subject = $existing.subject
            Created = $false
        }
    }

    $payload = $Definition | ConvertTo-Json -Compress -Depth 5
    $payloadPath = Join-Path $PSScriptRoot ".$($Definition.name).federated-credential.json"

    try {
        Set-Content -Path $payloadPath -Value $payload -Encoding utf8NoBOM -NoNewline
        $created = Invoke-AzJson -Arguments @(
            "ad", "app", "federated-credential", "create",
            "--id", $AppObjectId,
            "--parameters", "@$payloadPath"
        ) -FailureMessage "Failed to create federated credential '$($Definition.name)'."
    }
    finally {
        if (Test-Path $payloadPath) {
            Remove-Item -Path $payloadPath -Force
        }
    }

    return [PSCustomObject]@{
        Name    = $created.name
        Subject = $created.subject
        Created = $true
    }
}

function Ensure-RoleAssignment {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Assignee,

        [Parameter(Mandatory = $true)]
        [string]$Role,

        [Parameter(Mandatory = $true)]
        [string]$Scope
    )

    # Role assignments are idempotent at the scope/role/assignee level.
    $existing = Invoke-AzJson -Arguments @(
        "role", "assignment", "list",
        "--assignee", $Assignee,
        "--role", $Role,
        "--scope", $Scope
    ) -FailureMessage "Failed to inspect RBAC role '$Role' on scope '$Scope'."

    if (@($existing).Count -gt 0) {
        return [PSCustomObject]@{
            Role    = $Role
            Scope   = $Scope
            Created = $false
        }
    }

    $null = Invoke-AzJson -Arguments @(
        "role", "assignment", "create",
        "--assignee", $Assignee,
        "--role", $Role,
        "--scope", $Scope
    ) -FailureMessage "Failed to create RBAC role '$Role' on scope '$Scope'."

    return [PSCustomObject]@{
        Role    = $Role
        Scope   = $Scope
        Created = $true
    }
}

try {
    # Validate the local workstation state before making any Azure or GitHub changes.
    Write-Host "Validating prerequisites..." -ForegroundColor Cyan

    foreach ($commandName in @("az", "gh")) {
        if (-not (Test-CommandAvailable -Name $commandName)) {
            throw "Required command '$commandName' is not available on PATH."
        }
    }

    Invoke-Az -Arguments @("account", "show") -FailureMessage "Azure CLI is not logged in. Run 'az login' first." | Out-Null
    Invoke-Gh -Arguments @("auth", "status") -FailureMessage "GitHub CLI is not logged in. Run 'gh auth login' first." | Out-Null

    $account = Invoke-AzJson -Arguments @("account", "show") -FailureMessage "Failed to read the active Azure subscription."
    $subscriptionId = $account.id
    $tenantId = $account.tenantId

    if ([string]::IsNullOrWhiteSpace($subscriptionId) -or [string]::IsNullOrWhiteSpace($tenantId)) {
        throw "Azure CLI returned an incomplete account context. Ensure the correct subscription is selected."
    }

    $repoSlug = "$GitHubOrg/$GitHubRepo"
    Invoke-Gh -Arguments @("repo", "view", $repoSlug, "--json", "nameWithOwner") -FailureMessage "Failed to access GitHub repository '$repoSlug'." | Out-Null

    $subscriptionScope = "/subscriptions/$subscriptionId"

    $null = Invoke-AzJson -Arguments @(
        "group", "show",
        "--name", $ResourceGroup
    ) -FailureMessage "Resource group '$ResourceGroup' was not found in the current subscription."

    # Auto-discover the target ACR from the provided resource group to avoid hardcoded names.
    $acrCandidates = Invoke-AzJson -Arguments @(
        "acr", "list",
        "--resource-group", $ResourceGroup
    ) -FailureMessage "Failed to list Azure Container Registries in resource group '$ResourceGroup'."

    $acrList = @($acrCandidates)
    if ($acrList.Count -eq 0) {
        throw "No Azure Container Registry was found in resource group '$ResourceGroup'."
    }

    if ($acrList.Count -gt 1) {
        $acrNames = ($acrList | ForEach-Object { $_.name }) -join ", "
        throw "Multiple Azure Container Registries were found in resource group '$ResourceGroup' ($acrNames). Keep a single ACR in the target resource group before running this bootstrap."
    }

    $acr = $acrList[0]
    $acrName = $acr.name
    $acrResourceId = $acr.id

    Write-Host "Ensuring Entra app registration '$AppName'..." -ForegroundColor Cyan
    $existingApps = Invoke-AzJson -Arguments @(
        "ad", "app", "list",
        "--display-name", $AppName
    ) -FailureMessage "Failed to search for existing app registrations named '$AppName'."

    $app = @($existingApps | Where-Object { $_.displayName -eq $AppName }) | Select-Object -First 1
    $createdApp = $false
    if ($null -eq $app) {
        $app = Invoke-AzJson -Arguments @(
            "ad", "app", "create",
            "--display-name", $AppName,
            "--sign-in-audience", "AzureADMyOrg"
        ) -FailureMessage "Failed to create app registration '$AppName'."
        $createdApp = $true
    }

    $appId = $app.appId
    $appObjectId = $app.id

    if ([string]::IsNullOrWhiteSpace($appId) -or [string]::IsNullOrWhiteSpace($appObjectId)) {
        throw "Unable to resolve app registration identifiers for '$AppName'."
    }

    Write-Host "Ensuring service principal..." -ForegroundColor Cyan
    $servicePrincipal = $null
    try {
        $servicePrincipal = Invoke-AzJson -Arguments @(
            "ad", "sp", "show",
            "--id", $appId
        ) -FailureMessage "Service principal lookup failed."
        $createdServicePrincipal = $false
    }
    catch {
        $servicePrincipal = Invoke-AzJson -Arguments @(
            "ad", "sp", "create",
            "--id", $appId
        ) -FailureMessage "Failed to create the service principal for app '$appId'."
        $createdServicePrincipal = $true
    }

    $servicePrincipalObjectId = $servicePrincipal.id

    Write-Host "Ensuring GitHub federated credentials..." -ForegroundColor Cyan
    $masterCredential = Ensure-FederatedCredential -AppObjectId $appObjectId -Definition @{
        name      = "github-$GitHubRepo-master"
        issuer    = "https://token.actions.githubusercontent.com"
        subject   = "repo:${GitHubOrg}/${GitHubRepo}:ref:refs/heads/master"
        audiences = @("api://AzureADTokenExchange")
    }

    $pullRequestCredential = Ensure-FederatedCredential -AppObjectId $appObjectId -Definition @{
        name      = "github-$GitHubRepo-pr"
        issuer    = "https://token.actions.githubusercontent.com"
        subject   = "repo:${GitHubOrg}/${GitHubRepo}:pull_request"
        audiences = @("api://AzureADTokenExchange")
    }

    Write-Host "Ensuring RBAC assignments..." -ForegroundColor Cyan
    # Subscription-scope deployments validate and create the resource group, so Contributor must exist at subscription scope.
    $contributorRole = Ensure-RoleAssignment -Assignee $appId -Role "Contributor" -Scope $subscriptionScope
    $acrPushRole = Ensure-RoleAssignment -Assignee $appId -Role "AcrPush" -Scope $acrResourceId

    # GitHub repository variables are overwritten in place, which keeps reruns safe.
    Write-Host "Setting GitHub repository variables..." -ForegroundColor Cyan
    $variables = [ordered]@{
        AZURE_CLIENT_ID      = $appId
        AZURE_TENANT_ID      = $tenantId
        AZURE_SUBSCRIPTION_ID = $subscriptionId
        ACR_NAME             = $acrName
        RESOURCE_GROUP       = $ResourceGroup
        ENVIRONMENT          = $Environment
    }

    foreach ($variable in $variables.GetEnumerator()) {
        Invoke-Gh -Arguments @(
            "variable", "set", $variable.Key,
            "--repo", $repoSlug,
            "--body", [string]$variable.Value
        ) -FailureMessage "Failed to set GitHub variable '$($variable.Key)' in '$repoSlug'." | Out-Null
    }

    Write-Host ""
    Write-Host "OIDC bootstrap summary" -ForegroundColor Green
    Write-Host "----------------------" -ForegroundColor Green
    Write-Host "Repository: $repoSlug"
    Write-Host "Subscription: $($account.name) ($subscriptionId)"
    Write-Host "Tenant ID: $tenantId"
    Write-Host "App Registration: $AppName"
    Write-Host "  - Client ID: $appId"
    Write-Host "  - Object ID: $appObjectId"
    Write-Host "  - Status: $(if ($createdApp) { 'Created' } else { 'Reused existing app' })"
    Write-Host "Service Principal:"
    Write-Host "  - Object ID: $servicePrincipalObjectId"
    Write-Host "  - Status: $(if ($createdServicePrincipal) { 'Created' } else { 'Reused existing service principal' })"
    Write-Host "Federated credentials:"
    foreach ($credential in @($masterCredential, $pullRequestCredential)) {
        Write-Host "  - $($credential.Name): $($credential.Subject) ($(if ($credential.Created) { 'Created' } else { 'Already existed' }))"
    }
    Write-Host "RBAC assignments:"
    foreach ($assignment in @($contributorRole, $acrPushRole)) {
        Write-Host "  - $($assignment.Role) on $($assignment.Scope) ($(if ($assignment.Created) { 'Created' } else { 'Already existed' }))"
    }
    Write-Host "GitHub variables set:"
    foreach ($key in $variables.Keys) {
        Write-Host "  - $key"
    }
    Write-Host "Next step: Run the build-deploy workflow to test."
}
catch {
    Write-Error $_
    exit 1
}
