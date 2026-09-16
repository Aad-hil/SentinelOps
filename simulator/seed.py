from simulator.generator import (
    generate_incident_deployments,
    generate_incident_logs,
    generate_incident_metrics,
    generate_incident_traces,
)
from simulator.incidents import INCIDENT_001


def main() -> None:
    incident = INCIDENT_001

    logs = generate_incident_logs(incident.detected_at)
    metrics = generate_incident_metrics(incident.detected_at)
    deployments = generate_incident_deployments(incident.detected_at)
    traces = generate_incident_traces(incident.detected_at)

    print(f"Incident: {incident.incident_id}")
    print(f"Service: {incident.service}")
    print(f"Severity: {incident.severity}")
    print()
    print(f"Logs generated: {len(logs)}")
    print(f"Metrics generated: {len(metrics)}")
    print(f"Deployments generated: {len(deployments)}")
    print(f"Trace spans generated: {len(traces)}")


if __name__ == "__main__":
    main()
