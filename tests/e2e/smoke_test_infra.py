from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

RESOURCE_GROUP = "rg-verdecora-simple-dev"
STORAGE_ACCOUNT = "stvdsdev4vtapr"
COSMOS_ACCOUNT = "cosmos-vds-dev-4vtapr"
SERVICE_BUS_NAMESPACE = "sb-vds-dev-4vtapr"
KEY_VAULT = "kv-vds-dev-4vtapr"
ACR_NAME = "acrvdsdev4vtapr"
DOC_INTELLIGENCE = "vds-docintell-dev-4vtapr"
AI_FOUNDRY = "vds-ais-dev-4vtapr"
CONTAINER_APP_ENV = "acae-verdecora-dev"
EVENT_GRID_TOPIC = "eg-st-albaranes-dev"
LOG_ANALYTICS = "log-albaranes-dev"
APP_INSIGHTS = "appi-albaranes-dev"
AZ_CLI = shutil.which("az") or shutil.which("az.cmd") or "az"

EXPECTED_TOP_LEVEL_RESOURCES = {
    STORAGE_ACCOUNT,
    COSMOS_ACCOUNT,
    KEY_VAULT,
    "vds-docintell-dev-4vtapr",
    ACR_NAME,
    LOG_ANALYTICS,
    "vds-email-dev-4vtapr",
    SERVICE_BUS_NAMESPACE,
    APP_INSIGHTS,
    "vds-acs-dev-4vtapr",
    EVENT_GRID_TOPIC,
    "ag-verdecora-ops-dev",
    "la-verdecora-bc-mcp-dev",
    "ma-verdecora-queue-depth-dev",
    "la-verdecora-upload-web-5xx-dev",
    "la-verdecora-docint-timeouts-dev",
    "la-verdecora-upload-web-auth-dev",
    "la-verdecora-agent-p95-dev",
    AI_FOUNDRY,
    CONTAINER_APP_ENV,
    "Failure Anomalies - appi-albaranes-dev",
    "la-verdecora-upload-web-abandoned-dev",
}


@dataclass(slots=True)
class CheckResult:
    name: str
    passed: bool
    details: str


def _run_az(*args: str) -> subprocess.CompletedProcess[str]:
    command = [AZ_CLI, *args]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(stderr or f"Azure CLI command failed: {' '.join(command)}")
    return completed


def _run_az_json(*args: str) -> Any:
    completed = _run_az(*args)
    stdout = completed.stdout.strip()
    return json.loads(stdout) if stdout else None


def _run_az_text(*args: str) -> str:
    completed = _run_az(*args)
    return completed.stdout.strip()


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _validate_resource_inventory() -> CheckResult:
    group = _run_az_json(
        "group",
        "show",
        "--name",
        RESOURCE_GROUP,
        "--query",
        "{name:name,location:location,state:properties.provisioningState}",
        "--output",
        "json",
    )
    _check(group["state"] == "Succeeded", f"resource group state is {group['state']!r}")

    resource_names = set(
        _run_az_json(
            "resource",
            "list",
            "--resource-group",
            RESOURCE_GROUP,
            "--query",
            "[].name",
            "--output",
            "json",
        )
    )
    missing = sorted(EXPECTED_TOP_LEVEL_RESOURCES - resource_names)
    _check(not missing, f"missing top-level resources: {', '.join(missing)}")

    return CheckResult(
        "Resource inventory",
        True,
        f"{group['name']} in {group['location']} is healthy and includes {len(resource_names)} resources.",
    )


def _validate_storage() -> CheckResult:
    account = _run_az_json(
        "storage",
        "account",
        "show",
        "--name",
        STORAGE_ACCOUNT,
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "{status:statusOfPrimary,publicAccess:publicNetworkAccess}",
        "--output",
        "json",
    )
    _check(account["status"] == "available", f"storage status is {account['status']!r}")
    _check(account["publicAccess"] == "Enabled", f"storage public access is {account['publicAccess']!r}")

    containers = _run_az_json(
        "storage",
        "container",
        "list",
        "--account-name",
        STORAGE_ACCOUNT,
        "--auth-mode",
        "login",
        "--query",
        "[].name",
        "--output",
        "json",
    )
    expected = {"albaranes-raw", "albaranes-processed", "dlq"}
    missing = sorted(expected - set(containers))
    _check(not missing, f"missing blob containers: {', '.join(missing)}")
    return CheckResult("Storage account", True, f"{STORAGE_ACCOUNT} is public and has {len(containers)} containers.")


def _validate_cosmos() -> CheckResult:
    account = _run_az_json(
        "cosmosdb",
        "show",
        "--name",
        COSMOS_ACCOUNT,
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "{status:provisioningState,publicAccess:publicNetworkAccess}",
        "--output",
        "json",
    )
    _check(account["status"] == "Succeeded", f"cosmos state is {account['status']!r}")
    _check(account["publicAccess"] == "Enabled", f"cosmos public access is {account['publicAccess']!r}")

    databases = _run_az_json(
        "cosmosdb",
        "sql",
        "database",
        "list",
        "--account-name",
        COSMOS_ACCOUNT,
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "[].name",
        "--output",
        "json",
    )
    _check("albaranes-db" in databases, "expected SQL database 'albaranes-db' not found")
    return CheckResult("Cosmos DB", True, f"{COSMOS_ACCOUNT} is public and exposes databases: {', '.join(databases)}.")


def _validate_service_bus() -> CheckResult:
    namespace = _run_az_json(
        "servicebus",
        "namespace",
        "show",
        "--name",
        SERVICE_BUS_NAMESPACE,
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "{status:status,publicAccess:publicNetworkAccess}",
        "--output",
        "json",
    )
    _check(namespace["status"] == "Active", f"service bus status is {namespace['status']!r}")
    _check(namespace["publicAccess"] == "Enabled", f"service bus public access is {namespace['publicAccess']!r}")

    queues = _run_az_json(
        "servicebus",
        "queue",
        "list",
        "--namespace-name",
        SERVICE_BUS_NAMESPACE,
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "[].name",
        "--output",
        "json",
    )
    topics = _run_az_json(
        "servicebus",
        "topic",
        "list",
        "--namespace-name",
        SERVICE_BUS_NAMESPACE,
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "[].name",
        "--output",
        "json",
    )
    _check({"extraccion-in", "extraccion-queue"}.issubset(queues), "expected Service Bus queues are missing")
    _check({"albaran-events", "hitl-decisions"}.issubset(topics), "expected Service Bus topics are missing")
    return CheckResult(
        "Service Bus",
        True,
        f"{SERVICE_BUS_NAMESPACE} is Active with {len(queues)} queues and {len(topics)} topics.",
    )


def _validate_key_vault() -> CheckResult:
    vault = _run_az_json(
        "keyvault",
        "show",
        "--name",
        KEY_VAULT,
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "{publicAccess:properties.publicNetworkAccess}",
        "--output",
        "json",
    )
    _check(vault["publicAccess"] == "Enabled", f"key vault public access is {vault['publicAccess']!r}")
    return CheckResult("Key Vault", True, f"{KEY_VAULT} public network access is enabled.")


def _validate_acr() -> CheckResult:
    registry = _run_az_json(
        "acr",
        "show",
        "--name",
        ACR_NAME,
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "{status:provisioningState,publicAccess:publicNetworkAccess,loginServer:loginServer}",
        "--output",
        "json",
    )
    _check(registry["status"] == "Succeeded", f"acr state is {registry['status']!r}")
    _check(registry["publicAccess"] == "Enabled", f"acr public access is {registry['publicAccess']!r}")

    login_server = _run_az_text(
        "acr",
        "login",
        "--name",
        ACR_NAME,
        "--expose-token",
        "--query",
        "loginServer",
        "--output",
        "tsv",
    )
    _check(login_server == registry["loginServer"], "acr token exchange returned an unexpected login server")
    return CheckResult("Container Registry", True, f"{ACR_NAME} is public and token exchange succeeded.")


def _validate_ai_services() -> CheckResult:
    services = []
    for name in (DOC_INTELLIGENCE, AI_FOUNDRY):
        details = _run_az_json(
            "cognitiveservices",
            "account",
            "show",
            "--name",
            name,
            "--resource-group",
            RESOURCE_GROUP,
            "--query",
            "{status:properties.provisioningState,publicAccess:properties.publicNetworkAccess,kind:kind}",
            "--output",
            "json",
        )
        _check(details["status"] == "Succeeded", f"{name} state is {details['status']!r}")
        _check(details["publicAccess"] == "Enabled", f"{name} public access is {details['publicAccess']!r}")
        services.append(f"{name} ({details['kind']})")
    return CheckResult("AI Services", True, "Validated: " + ", ".join(services) + ".")


def _validate_container_apps_environment() -> CheckResult:
    environments = _run_az_json(
        "containerapp",
        "env",
        "list",
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "[].name",
        "--output",
        "json",
    )
    _check(CONTAINER_APP_ENV in environments, f"container app environment {CONTAINER_APP_ENV!r} not found")
    return CheckResult("Container Apps environment", True, f"{CONTAINER_APP_ENV} exists.")


def _validate_container_apps() -> CheckResult:
    apps = _run_az_json(
        "containerapp",
        "list",
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "[].{name:name,identity:identity.type}",
        "--output",
        "json",
    )
    _check(bool(apps), "no Container Apps are deployed")
    missing_identity = [app["name"] for app in apps if not app.get("identity")]
    _check(not missing_identity, f"missing managed identity on: {', '.join(missing_identity)}")
    return CheckResult("Container Apps + identity", True, f"{len(apps)} Container App(s) deployed with identity.")


def _validate_event_grid() -> CheckResult:
    topics = _run_az_json(
        "eventgrid",
        "system-topic",
        "list",
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "[].{name:name,state:provisioningState}",
        "--output",
        "json",
    )
    state_map = {topic["name"]: topic["state"] for topic in topics}
    _check(EVENT_GRID_TOPIC in state_map, f"event grid topic {EVENT_GRID_TOPIC!r} not found")
    _check(state_map[EVENT_GRID_TOPIC] == "Succeeded", f"event grid topic state is {state_map[EVENT_GRID_TOPIC]!r}")
    return CheckResult("Event Grid", True, f"{EVENT_GRID_TOPIC} is {state_map[EVENT_GRID_TOPIC]}.")


def _validate_monitoring() -> CheckResult:
    workspace = _run_az_json(
        "monitor",
        "log-analytics",
        "workspace",
        "show",
        "--resource-group",
        RESOURCE_GROUP,
        "--workspace-name",
        LOG_ANALYTICS,
        "--query",
        "{status:provisioningState,ingestion:publicNetworkAccessForIngestion,query:publicNetworkAccessForQuery}",
        "--output",
        "json",
    )
    _check(workspace["status"] == "Succeeded", f"log analytics state is {workspace['status']!r}")
    _check(workspace["ingestion"] == "Enabled", f"log analytics ingestion access is {workspace['ingestion']!r}")
    _check(workspace["query"] == "Enabled", f"log analytics query access is {workspace['query']!r}")

    app_insights = _run_az_json(
        "monitor",
        "app-insights",
        "component",
        "show",
        "--app",
        APP_INSIGHTS,
        "--resource-group",
        RESOURCE_GROUP,
        "--query",
        "{status:provisioningState,ingestion:publicNetworkAccessForIngestion,query:publicNetworkAccessForQuery}",
        "--output",
        "json",
    )
    _check(app_insights["status"] == "Succeeded", f"app insights state is {app_insights['status']!r}")
    _check(app_insights["ingestion"] == "Enabled", f"app insights ingestion access is {app_insights['ingestion']!r}")
    _check(app_insights["query"] == "Enabled", f"app insights query access is {app_insights['query']!r}")
    return CheckResult("Monitoring", True, f"{LOG_ANALYTICS} and {APP_INSIGHTS} are healthy and public.")


def _run_check(name: str, operation: Callable[[], CheckResult]) -> CheckResult:
    try:
        return operation()
    except Exception as exc:  # noqa: BLE001 - CLI smoke test should trap and report all failures.
        return CheckResult(name, False, str(exc))


def main() -> int:
    checks = [
        _run_check("Resource inventory", _validate_resource_inventory),
        _run_check("Storage account", _validate_storage),
        _run_check("Cosmos DB", _validate_cosmos),
        _run_check("Service Bus", _validate_service_bus),
        _run_check("Key Vault", _validate_key_vault),
        _run_check("Container Registry", _validate_acr),
        _run_check("AI Services", _validate_ai_services),
        _run_check("Container Apps environment", _validate_container_apps_environment),
        _run_check("Container Apps + identity", _validate_container_apps),
        _run_check("Event Grid", _validate_event_grid),
        _run_check("Monitoring", _validate_monitoring),
    ]

    failed = False
    for result in checks:
        marker = "PASS" if result.passed else "FAIL"
        print(f"[{marker}] {result.name}: {result.details}")
        failed = failed or not result.passed

    print()
    print("Overall result: FAIL" if failed else "Overall result: PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
