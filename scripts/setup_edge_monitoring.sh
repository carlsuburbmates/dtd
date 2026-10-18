#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# DTD Operations: Independent Decoupled Edge Monitoring & Alert Policy Setup
#
# Solves the "Monitoring the Monitor" circular dependency:
# When Cloud Run crashes, scales to zero with an error, or encounters an internal
# failure, in-app /ops console cannot load to alert the solo owner.
#
# This script provisions an independent, external Google Cloud Monitoring
# global edge uptime check and email alert policy routing to the operator.
# ==============================================================================

PROJECT_ID="${1:-dogtrainersdirectory-dev}"
ALERT_EMAIL="${2:-admin@dogtrainersdirectory.com.au}"

if [ "${PROJECT_ID}" = "gen-lang-client-0028123502" ]; then
  HOSTNAME="dogtrainersdirectory.com.au"
  DISPLAY_NAME="DTD Production API Edge Uptime Check"
else
  HOSTNAME="dtd-api-dev-625222421634.australia-southeast1.run.app"
  DISPLAY_NAME="DTD Sandbox API Edge Uptime Check"
fi

echo "=================================================================="
echo "Configuring Independent Edge Observability for ${PROJECT_ID}"
echo "Hostname: ${HOSTNAME}"
echo "Alert Destination: ${ALERT_EMAIL}"
echo "=================================================================="

# 1. Create or Find Email Notification Channel
echo "🔍 [1/3] Checking Email Notification Channel..."
CHANNEL_JSON=$(gcloud monitoring channels list --project="${PROJECT_ID}" --filter="type=email AND labels.email_address=${ALERT_EMAIL}" --format="json" 2>/dev/null || echo "[]")
CHANNEL_ID=$(echo "${CHANNEL_JSON}" | python3 -c '
import sys, json
data = json.load(sys.stdin)
if isinstance(data, list) and len(data) > 0:
    print(data[0].get("name", ""))
' 2>/dev/null || echo "")

if [ -z "${CHANNEL_ID}" ]; then
  echo "Creating Notification Channel for ${ALERT_EMAIL}..."
  CHANNEL_NAME=$(gcloud monitoring channels create \
    --project="${PROJECT_ID}" \
    --display-name="DTD Owner Escalation (${ALERT_EMAIL})" \
    --type=email \
    --channel-content="email_address=${ALERT_EMAIL}" \
    --format="value(name)")
  CHANNEL_ID="${CHANNEL_NAME}"
  echo "✅ Created Notification Channel: ${CHANNEL_ID}"
else
  echo "✅ Reusing Existing Notification Channel: ${CHANNEL_ID}"
fi

# 2. Create or Update Global Uptime Check
echo "🔍 [2/3] Configuring Global Edge Uptime Check on /api/health..."
EXISTING_UPTIME=$(gcloud monitoring uptime list-configs --project="${PROJECT_ID}" --filter="displayName='${DISPLAY_NAME}'" --format="value(name)" 2>/dev/null || echo "")

if [ -z "${EXISTING_UPTIME}" ]; then
  echo "Creating Uptime Check '${DISPLAY_NAME}'..."
  gcloud monitoring uptime create "${DISPLAY_NAME}" \
    --project="${PROJECT_ID}" \
    --display-name="${DISPLAY_NAME}" \
    --protocol=HTTPS \
    --hostname="${HOSTNAME}" \
    --path="/api/health" \
    --check-interval=5m \
    --timeout=10s
  echo "✅ Created Uptime Check."
else
  echo "✅ Uptime Check exists: ${EXISTING_UPTIME}"
fi

# 3. Configure Alerting Policy
echo "🔍 [3/3] Configuring Edge Alerting Policy..."
cat <<EOF > /tmp/dtd_uptime_alert_policy.json
{
  "displayName": "DTD API Edge Health Failure (Immediate Owner Escalation)",
  "documentation": {
    "content": "EMERGENCY: The external DTD /api/health probe has failed from multiple global edge locations. Cloud Run API or database is unreachable. Immediate owner investigation required.",
    "mimeType": "text/markdown"
  },
  "userLabels": {
    "severity": "critical",
    "domain": "site_availability"
  },
  "conditions": [
    {
      "displayName": "Uptime Check Failure on /api/health",
      "conditionThreshold": {
        "filter": "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\"",
        "comparison": "COMPARISON_GT",
        "thresholdValue": 1,
        "duration": "60s",
        "aggregations": [
          {
            "alignmentPeriod": "300s",
            "perSeriesAligner": "ALIGN_NEXT_OLDER",
            "crossSeriesReducer": "REDUCE_COUNT_FALSE"
          }
        ]
      }
    }
  ],
  "combiner": "OR",
  "enabled": true,
  "notificationChannels": [
    "${CHANNEL_ID}"
  ]
}
EOF

EXISTING_POLICY=$(gcloud alpha monitoring policies list --project="${PROJECT_ID}" --filter="displayName='DTD API Edge Health Failure (Immediate Owner Escalation)'" --format="value(name)" 2>/dev/null || echo "")

if [ -z "${EXISTING_POLICY}" ]; then
  gcloud alpha monitoring policies create \
    --project="${PROJECT_ID}" \
    --policy-from-file=/tmp/dtd_uptime_alert_policy.json
  echo "✅ Created Edge Alert Policy linked to ${ALERT_EMAIL}."
else
  echo "✅ Updating Existing Alert Policy: ${EXISTING_POLICY}"
  gcloud alpha monitoring policies update "${EXISTING_POLICY}" \
    --project="${PROJECT_ID}" \
    --policy-from-file=/tmp/dtd_uptime_alert_policy.json
fi

rm -f /tmp/dtd_uptime_alert_policy.json
echo "=================================================================="
echo "🎉 Decoupled Edge Monitoring Setup Complete for ${PROJECT_ID}."
echo "Probing: https://${HOSTNAME}/api/health every 5 minutes."
echo "Outages will notify: ${ALERT_EMAIL}"
echo "=================================================================="
