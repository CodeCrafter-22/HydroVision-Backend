# Automation Workflows (n8n & Webhooks)

This directory contains scheduled workflows, incident alert dispatchers, and integration triggers for the HydroVision platform.

## Workflows Included:
- `WF-00_error-handler.json`: Centralized workflow error handling and alerting.
- `WF-01_source-health-check.json`: Source availability & health monitoring check.
- `WF-02_scheduled-ingestion-trigger.json`: Scheduled 15-minute ingestion trigger for upstream data sources.
- `WF-03_ingestion-status-alert.json`: Ingestion failure notification webhook receiver and dispatcher.
- `WF-04_daily-summary-report.json`: Daily flood risk summary and operational reporting.
- `WF-05_threshold-anomaly-alerting.json`: Real-time anomaly detection and threshold breach alerts.
