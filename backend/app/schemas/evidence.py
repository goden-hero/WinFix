from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EvidenceCategory(str, Enum):
    PERFORMANCE = "performance"
    SYSTEM_HEALTH = "system_health"
    CRASH = "crash"
    OPTIMIZATION = "optimization"
    PRIVACY = "privacy"
    WINDOWS_UPDATE = "windows_update"
    BATTERY = "battery"
    EXPLORER = "explorer"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Evidence(BaseModel):
    """A normalized, display-ready observation from a diagnostic tool."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    category: EvidenceCategory
    severity: Severity
    title: str
    description: str
    source: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = Field(default_factory=dict)
