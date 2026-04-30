#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ -f .env ]; then
  eval "$(
    python3 - <<'PY'
import shlex
from pathlib import Path
for raw_line in Path('.env').read_text().splitlines():
    line = raw_line.strip()
    if not line or line.startswith('#') or '=' not in line:
        continue
    k, v = line.split('=', 1)
    k = k.strip()
    v = v.strip()
    if k.startswith('export '):
        k = k[len('export '):].strip()
    if not k:
        continue
    print(f"export {k}={shlex.quote(v)}")
PY
  )"
fi

fail=0

if command -v rg >/dev/null 2>&1; then
  LOG_GREP="rg -q"
else
  LOG_GREP="grep -Eq"
fi

echo "[stage-a] verify runtime baseline"
stage_a_mode="${STAGE_A_MODE:-local}"
if [ "$stage_a_mode" != "local" ] && [ "$stage_a_mode" != "remote" ]; then
  echo "[stage-a] FAIL: STAGE_A_MODE must be 'local' or 'remote' (got '$stage_a_mode')"
  exit 1
fi
echo "[stage-a] mode=$stage_a_mode"

require_var() {
  local key="$1"
  if [ -z "${!key-}" ]; then
    echo "[stage-a] MISSING: $key"
    fail=1
  fi
}

require_var RENDER_API_KEY
require_var MONGODB_ATLAS_PUBLIC_KEY
require_var MONGODB_ATLAS_PRIVATE_KEY
require_var MONGODB_ATLAS_PROJECT_ID
if [ "$stage_a_mode" = "local" ]; then
  require_var MONGO_URL
  require_var DB_NAME
else
  require_var REMOTE_BACKEND_URL
fi

echo "[stage-a] Render services"
render_http="$(curl -sS -o /tmp/stagea_render_services.json -w "%{http_code}" --max-time 30 \
  -H "Accept: application/json" \
  -H "Authorization: Bearer ${RENDER_API_KEY-}" \
  "https://api.render.com/v1/services?limit=100" || true)"
echo "  render_http=$render_http"
if [ "$render_http" != "200" ]; then
  echo "  FAIL: cannot list Render services"
  if [ "$render_http" = "402" ]; then
    echo "  HINT: Render billing/payment method is required before service creation APIs are usable."
  fi
  fail=1
else
  python3 - <<'PY'
import json
from pathlib import Path
try:
    data=json.loads(Path('/tmp/stagea_render_services.json').read_text() or "[]")
except Exception:
    print("  render_parse_error=true")
    raise
rows=data if isinstance(data,list) else data.get("items",[])
services=[]
for row in rows:
    if isinstance(row, dict) and isinstance(row.get("service"), dict):
        services.append(row["service"])
    elif isinstance(row, dict):
        services.append(row)
names={s.get("name") for s in services if isinstance(s,dict)}
print(f"  render_service_count={len(services)}")
for n in ("dtd-api","dtd-worker"):
    print(f"  render_has_{n}={n in names}")
PY
  if ! python3 - <<'PY'
import json,sys
from pathlib import Path
try:
    data=json.loads(Path('/tmp/stagea_render_services.json').read_text() or "[]")
except Exception:
    sys.exit(1)
rows=data if isinstance(data,list) else data.get("items",[])
services=[]
for row in rows:
    if isinstance(row, dict) and isinstance(row.get("service"), dict):
        services.append(row["service"])
    elif isinstance(row, dict):
        services.append(row)
names={s.get("name") for s in services if isinstance(s,dict)}
ok=("dtd-api" in names and "dtd-worker" in names)
sys.exit(0 if ok else 1)
PY
  then
    echo "  FAIL: missing required Render services (dtd-api, dtd-worker)"
    fail=1
  fi
fi

echo "[stage-a] Atlas baseline"
atlas_clusters_http="$(curl -sS -o /tmp/stagea_atlas_clusters.json -w "%{http_code}" --max-time 30 --digest \
  -u "${MONGODB_ATLAS_PUBLIC_KEY-}:${MONGODB_ATLAS_PRIVATE_KEY-}" \
  -H "Accept: application/vnd.atlas.2023-01-01+json" \
  "https://cloud.mongodb.com/api/atlas/v2/groups/${MONGODB_ATLAS_PROJECT_ID-}/clusters" || true)"
echo "  atlas_clusters_http=$atlas_clusters_http"
if [ "$atlas_clusters_http" != "200" ]; then
  echo "  FAIL: cannot list Atlas clusters"
  fail=1
else
  python3 - <<'PY'
import json
from pathlib import Path
obj=json.loads(Path('/tmp/stagea_atlas_clusters.json').read_text())
res=obj.get("results",[])
print(f"  atlas_cluster_count={len(res)}")
for c in res:
    print(f"  atlas_cluster={c.get('name')} state={c.get('stateName')}")
PY
fi

atlas_users_http="$(curl -sS -o /tmp/stagea_atlas_users.json -w "%{http_code}" --max-time 30 --digest \
  -u "${MONGODB_ATLAS_PUBLIC_KEY-}:${MONGODB_ATLAS_PRIVATE_KEY-}" \
  -H "Accept: application/vnd.atlas.2023-01-01+json" \
  "https://cloud.mongodb.com/api/atlas/v2/groups/${MONGODB_ATLAS_PROJECT_ID-}/databaseUsers/admin" || true)"
echo "  atlas_users_http=$atlas_users_http"
if [ "$atlas_users_http" != "200" ]; then
  echo "  FAIL: cannot list Atlas DB users"
  fail=1
else
  if ! python3 - <<'PY'
import json,sys
from pathlib import Path
obj=json.loads(Path('/tmp/stagea_atlas_users.json').read_text())
users=obj.get("results",[])
names={u.get("username") for u in users}
print(f"  atlas_db_user_count={len(users)}")
print(f"  atlas_has_dtd_app={'dtd_app' in names}")
sys.exit(0 if "dtd_app" in names else 1)
PY
  then
    echo "  FAIL: Atlas DB user dtd_app missing"
    fail=1
  fi
fi

atlas_access_http="$(curl -sS -o /tmp/stagea_atlas_access.json -w "%{http_code}" --max-time 30 --digest \
  -u "${MONGODB_ATLAS_PUBLIC_KEY-}:${MONGODB_ATLAS_PRIVATE_KEY-}" \
  -H "Accept: application/vnd.atlas.2023-01-01+json" \
  "https://cloud.mongodb.com/api/atlas/v2/groups/${MONGODB_ATLAS_PROJECT_ID-}/accessList" || true)"
echo "  atlas_access_http=$atlas_access_http"
if [ "$atlas_access_http" != "200" ]; then
  echo "  FAIL: cannot list Atlas access list"
  fail=1
else
  if ! python3 - <<'PY'
import json,sys
from pathlib import Path
obj=json.loads(Path('/tmp/stagea_atlas_access.json').read_text())
rules=obj.get("results",[])
ok=False
for r in rules:
    if r.get("cidrBlock")=="0.0.0.0/0" or r.get("ipAddress")=="0.0.0.0":
        ok=True
print(f"  atlas_access_rule_count={len(rules)}")
print(f"  atlas_has_0_0_0_0_0={ok}")
sys.exit(0 if ok else 1)
PY
  then
    echo "  FAIL: 0.0.0.0/0 Atlas access rule missing"
    fail=1
  fi
fi

if [ "$stage_a_mode" = "local" ]; then
  echo "[stage-a] Local restart/readiness"
  docker compose up -d backend worker >/tmp/stagea_compose_up.log 2>&1 || {
    cat /tmp/stagea_compose_up.log
    echo "  FAIL: docker compose up backend worker failed"
    fail=1
  }

  config_http="000"
  for _ in {1..20}; do
    config_http="$(curl -sS -o /tmp/stagea_config.json -w "%{http_code}" --max-time 10 "http://localhost:8001/api/config" || true)"
    [ "$config_http" = "200" ] && break
    sleep 1
  done
  echo "  api_config_http=$config_http"
  if [ "$config_http" != "200" ]; then
    echo "  FAIL: /api/config unavailable"
    if docker compose logs backend --tail=120 | sh -c "$LOG_GREP 'SSL handshake failed: .*UNEXPECTED_EOF_WHILE_READING'"; then
      echo "  HINT: Atlas TLS handshake is failing from runtime environment."
    fi
    fail=1
  fi

  worker_log_ok=0
  for _ in {1..20}; do
    if docker compose logs worker --tail=400 | sh -c "$LOG_GREP 'scheduled [0-9]+ autonomous loops'"; then
      worker_log_ok=1
      break
    fi
    sleep 1
  done
  if [ "$worker_log_ok" -ne 1 ]; then
    echo "  FAIL: worker loop scheduling log not found"
    fail=1
  else
    echo "  worker_schedule_log=present"
  fi
else
  echo "[stage-a] Remote backend readiness"
  remote_base="${REMOTE_BACKEND_URL-}"
  if [ -z "$remote_base" ]; then
    echo "  FAIL: REMOTE_BACKEND_URL is required in remote mode"
    fail=1
  else
    remote_base="${remote_base%/}"
    config_http="000"
    for _ in {1..20}; do
      config_http="$(curl -sS -o /tmp/stagea_remote_config.json -w "%{http_code}" --max-time 15 "${remote_base}/api/config" || true)"
      [ "$config_http" = "200" ] && break
      sleep 1
    done
    echo "  remote_api_config_http=$config_http url=${remote_base}/api/config"
    if [ "$config_http" != "200" ]; then
      echo "  FAIL: remote /api/config unavailable"
      fail=1
    fi
  fi

  if [ "${render_http:-000}" = "200" ] && python3 - <<'PY'
import json,sys
from pathlib import Path
try:
    raw = Path('/tmp/stagea_render_services.json').read_text()
except FileNotFoundError:
    print("  render_runtime_health_error=missing Render services response file")
    sys.exit(1)

try:
    obj=json.loads(raw) if raw.strip() else []
except json.JSONDecodeError:
    print("  render_runtime_health_error=Render services response was not valid JSON")
    sys.exit(1)
rows=obj if isinstance(obj,list) else obj.get("items",[])
services=[]
for row in rows:
    if isinstance(row, dict) and isinstance(row.get("service"), dict):
        services.append(row["service"])
    elif isinstance(row, dict):
        services.append(row)
by_name={s.get("name"):s for s in services if isinstance(s,dict)}
api=by_name.get("dtd-api",{})
worker=by_name.get("dtd-worker",{})
api_ok=bool(api) and str(api.get("suspended","")).lower() == "not_suspended"
worker_ok=bool(worker) and str(worker.get("suspended","")).lower() == "not_suspended"
print(f"  render_dtd_api_runtime={(api.get('serviceDetails') or {}).get('runtime')}")
print(f"  render_dtd_api_suspended={api.get('suspended')}")
print(f"  render_dtd_worker_runtime={(worker.get('serviceDetails') or {}).get('runtime')}")
print(f"  render_dtd_worker_suspended={worker.get('suspended')}")
sys.exit(0 if (api_ok and worker_ok) else 1)
PY
  then
    echo "  render_runtime_health=ok"
  else
    echo "  FAIL: Render runtime health check failed for dtd-api and/or dtd-worker"
    fail=1
  fi
fi

if [ "$fail" -ne 0 ]; then
  echo "[stage-a] RESULT=FAIL"
  exit 1
fi

echo "[stage-a] RESULT=PASS"
