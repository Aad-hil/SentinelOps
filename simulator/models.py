from dataclasses import dataclass
from datetime import datetime
from typing import Literal


LogLevel = Literal["DEBUG", "INFO", "WARN", "ERROR"]
Severity = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


@dataclass(frozen=True)
class LogEvent:
    timestamp: datetime
    service: str
    level: LogLevel
    message: str


@dataclass(frozen=True)
class MetricPoint:
    timestamp: datetime
    metric_name: str
    service: str
    value: float


@dataclass(frozen=True)
class DeploymentEvent:
    timestamp: datetime
    service: str
    version: str
    previous_version: str
    changes: dict[str, str]


@dataclass(frozen=True)
class TraceSpan:
    timestamp: datetime
    trace_id: str
    service: str
    operation: str
    duration_ms: float
    status: Literal["OK", "ERROR"]


@dataclass(frozen=True)
class Incident:
    incident_id: str
    service: str
    severity: Severity
    title: str
    description: str
    started_at: datetime
    detected_at: datetime


@dataclass(frozen=True)
class GroundTruth:
    root_cause: str
    trigger: str
    affected_component: str
    mitigation: str
    contributing_factors: tuple[str, ...]


@dataclass(frozen=True)
class IncidentScenario:
    incident: Incident
    logs: tuple[LogEvent, ...]
    metrics: tuple[MetricPoint, ...]
    deployments: tuple[DeploymentEvent, ...]
    traces: tuple[TraceSpan, ...]
    ground_truth: GroundTruth
