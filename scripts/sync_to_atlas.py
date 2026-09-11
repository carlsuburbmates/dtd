import os
import sys
import time
import json
import secrets
import urllib.parse
import requests
from requests.auth import HTTPDigestAuth
import dotenv
import pymongo

def check_cluster_status(gid, pub, priv):
    url = f"https://cloud.mongodb.com/api/atlas/v2/groups/{gid}/clusters/DTD"
    r = requests.get(url, auth=HTTPDigestAuth(pub, priv), headers={"Accept": "application/vnd.atlas.2023-01-01+json"})
    if r.status_code != 200:
        return None, None
    data = r.json()
    return data.get("stateName"), data.get("paused")

def set_dtd_app_password(gid, pub, priv, new_pw):
    url = f"https://cloud.mongodb.com/api/atlas/v2/groups/{gid}/databaseUsers/admin/dtd_app"
    payload = {
        "password": new_pw,
        "roles": [
            {"databaseName": "dtd", "roleName": "readWrite"},
            {"databaseName": "admin", "roleName": "readWriteAnyDatabase"}
        ]
    }
    r = requests.patch(
        url,
        auth=HTTPDigestAuth(pub, priv),
        headers={"Accept": "application/vnd.atlas.2023-01-01+json", "Content-Type": "application/json"},
        json=payload
    )
    return r.status_code in (200, 201)

def main():
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dotenv.dotenv_values(os.path.join(root_dir, ".env"))
    pub = env.get("MONGODB_ATLAS_PUBLIC_KEY")
    priv = env.get("MONGODB_ATLAS_PRIVATE_KEY")
    gid = env.get("MONGODB_ATLAS_PROJECT_ID")

    if not all([pub, priv, gid]):
        print("Missing MONGODB_ATLAS credentials in .env")
        sys.exit(1)

    print("Checking Atlas cluster status...")
    state, paused = check_cluster_status(gid, pub, priv)
    print(f"Cluster DTD: state={state}, paused={paused}")

    if paused:
        print("Cluster is still PAUSED. Owner must click 'Resume' in Atlas Web UI.")
        print(f"URL: https://cloud.mongodb.com/v2/{gid}#/clusters")
        sys.exit(2)

    print("Cluster is active! Setting application user password...")
    new_pw = secrets.token_urlsafe(32)
    if not set_dtd_app_password(gid, pub, priv, new_pw):
        print("Failed to set dtd_app password in Atlas")
        sys.exit(1)

    escaped_pw = urllib.parse.quote_plus(new_pw)
    atlas_uri = f"mongodb+srv://dtd_app:{escaped_pw}@dtd.e34l3on.mongodb.net/dtd?retryWrites=true&w=majority"

    print("Testing connection to Atlas cluster (waiting up to 30s for user propagation)...")
    connected = False
    for attempt in range(6):
        try:
            client = pymongo.MongoClient(atlas_uri, serverSelectionTimeoutMS=5000)
            client.admin.command("ping")
            connected = True
            print("Atlas ping succeeded!")
            break
        except Exception as e:
            print(f"Attempt {attempt + 1}: ping failed ({e}), waiting 5s...")
            time.sleep(5)

    if not connected:
        print("Could not connect to Atlas after 30s")
        sys.exit(1)

    print("\nStarting data sync from local MongoDB to Atlas...")
    local_client = pymongo.MongoClient("mongodb://localhost:27017")
    local_db = local_client["dtd"]
    remote_client = pymongo.MongoClient(atlas_uri)
    remote_db = remote_client["dtd"]

    collections = local_db.list_collection_names()
    for coll_name in collections:
        docs = list(local_db[coll_name].find({}))
        if docs:
            # Drop remote collection first to ensure clean sync
            remote_db[coll_name].drop()
            remote_db[coll_name].insert_many(docs)
            print(f"Synced {len(docs)} documents into {coll_name}")
        else:
            print(f"Collection {coll_name} is empty (skipped)")

    print("\nUpdating Secret Manager dtd-mongo-url...")
    import subprocess
    proc = subprocess.run(
        ["gcloud", "secrets", "versions", "add", "dtd-mongo-url", "--data-file=-", "--project=gen-lang-client-0028123502"],
        input=atlas_uri,
        capture_output=True,
        text=True
    )
    if proc.returncode == 0:
        print("Secret Manager dtd-mongo-url updated successfully!")
    else:
        print(f"Failed to update Secret Manager: {proc.stderr}")
        sys.exit(1)

    print("\nRestarting Cloud Run dtd-api revision...")
    restart_proc = subprocess.run(
        ["gcloud", "run", "services", "update", "dtd-api", "--project=gen-lang-client-0028123502", "--region=australia-southeast1", "--update-env-vars", f"FORCE_RESTART={int(time.time())}"],
        capture_output=True,
        text=True
    )
    print("Cloud Run update completed with returncode:", restart_proc.returncode)

    print("\nVerifying Cloud Run health...")
    time.sleep(10)
    for i in range(6):
        try:
            r = requests.get("https://dtd-api-870311309192.australia-southeast1.run.app/api/health", timeout=10)
            print(f"Health check attempt {i+1}: {r.status_code} - {r.text}")
            if r.status_code == 200 and r.json().get("database") == "available":
                print("\nSUCCESS: Cloud Run backend is fully healthy and connected to Atlas database!")
                break
        except Exception as e:
            print(f"Health check attempt {i+1} error: {e}")
        time.sleep(5)

if __name__ == "__main__":
    main()
