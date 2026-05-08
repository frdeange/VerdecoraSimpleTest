from __future__ import annotations

import pytest

from src.services.hitl_webform.config import HITLWebformConfig


@pytest.mark.unit
def test_public_base_url_normalizes_direct_aca_hostname() -> None:
    config = HITLWebformConfig(public_base_url="hitl-webform.swedencentral.azurecontainerapps.io/")

    assert config.public_base_url == "https://hitl-webform.swedencentral.azurecontainerapps.io"
    assert config.build_public_url("/review/alb-123") == "https://hitl-webform.swedencentral.azurecontainerapps.io/review/alb-123"
