import os
import tarfile
import json
from pathlib import Path
from lxml import etree
from tqdm import tqdm

from zenodo_dump_functions import harvest_all_zenodo_from_dump, build_graph
import requests
import re

# Variables

DUMP_PATH       = "records-xml.tar.gz"
OUTPUT_JSON     = "zenodo_wind_energy_records.jsonl"           # 1st round of filtering with lower threshold of 0.35
NEW_OUTPUT_JSON = "zenodo_wind_energy_records_update.jsonl"    # 2nd round of filtering with higher threshold

RELEVANCE_QUERY = (
        "Wind energy datasets, including measurements of wind speed, wind direction, turbine performance, SCADA data, aerodynamics, wake effects, offshore wind, and condition monitoring."
)

WIND_ENERGY_KEYWORDS = (
    "wind energy", "wind turbine", "wind farm",
    "wind speed", "wind direction", "turbulence",
    "rotor", "blade", "aerodynamic", "wake",
    "SCADA", "condition monitoring", "time series",
    "offshore wind", "floating wind",
    "maintenance", "fault detection", "power curve",
)

ZENODO_API    = "https://zenodo.org/api/records/"
ZENODO_TOKEN  = os.getenv("ZENODO_TOKEN")  # export  ZENODO_TOKEN='personal_access_token'
WINDLAB_URL   = "https://windlab.hlrs.de/api/3/action/package_create"
WINDLAB_TOKEN = os.getenv("WINDLAB_TOKEN") # export WINDLAB_TOKEN='ckan_token'
WINDLAB_ORG   = "zenodo"

# Helper functions

def slugify(value): 
    value = value.lower()
    value = re.sub(r"[^a-z0-9-]+", "-", value)
    return value.strip("-")

def fetch_zenodo_record(record_id):
    headers = {
        "Authorization": f"Bearer {ZENODO_TOKEN}"
    }

    r = requests.get(ZENODO_API + record_id, headers=headers, timeout=30)

    if r.status_code != 200:
        print(f"Failed Zenodo fetch {record_id}")
        return None

    return r.json()

def map_zenodo_to_windlab(z_record):
    metadata = z_record.get("metadata", {})
    files = z_record.get("files", [])

    title = metadata.get("title", "Untitled")
    description = metadata.get("description", "")
    doi = metadata.get("doi")
    version = metadata.get("version", "1")

    creators = metadata.get("creators", [])
    author_names = ", ".join(c.get("name") for c in creators if c.get("name"))

    license_id = metadata.get("license", {}).get("id", "cc-by")

    # URL friendly name
    package_id = slugify(f"zenodo-{z_record['id']}")

    resources = []

    for f in files:
        resources.append({
            "name": f.get("key"),
            "url": f.get("links", {}).get("self"),
            "format": detect_format(f.get("key")),
            "description": f.get("key")
        })

    return {
        "name":  package_id,
        "title": title,
        "notes": description,
        "owner_org": WINDLAB_ORG,
        "url": f"https://doi.org/{doi}" if doi else z_record.get("links", {}).get("self"),
        "license_id": license_id,
        "version": version,
        "author": author_names,
        #"maintainer": author_names,
        "resources": resources
    }

def detect_format(filename):
    if not filename:
        return "DATA"

    ext = filename.split(".")[-1].upper()

    if ext in ["CSV", "JSON", "XML", "XLSX", "TXT"]:
        return ext
    return "DATA"


def upload_to_windlab(dataset_record):
    headers = {
        "Authorization": WINDLAB_TOKEN,
        "Content-Type": "application/json" }

    response = requests.post(WINDLAB_URL, headers=headers, data=json.dumps(dataset_record), timeout=30)

    if response.status_code != 200:
        print("CKAN error:", response.text)
        return False
    
    result = response.json()
    if not result.get("success"):
        print("CKAN API failure:", result)
        return False

    return True

# Prerequisite: curl -O https://zenodo.org/api/exporter/records-xml.tar.gz

if __name__ == "__main__":
    if os.path.isfile(OUTPUT_JSON) and os.path.isfile(NEW_OUTPUT_JSON):
        print("Uploading...")
        with open(NEW_OUTPUT_JSON, "r", encoding="utf-8") as f:
            for line in f:
                record    = json.loads(line)
                record_id = record["url"].rstrip("/").split("/")[-1]
                zenodo_record = fetch_zenodo_record(record_id)
                if not zenodo_record:
                    continue

                ckan_package = map_zenodo_to_windlab(zenodo_record)
                success      = upload_to_windlab(ckan_package)

                if success:
                    print("Created: ", ckan_package["name"])
                else:
                    print("Failed:",   ckan_package["name"])

        print("...Uploaded")

    elif os.path.isfile(OUTPUT_JSON) and not os.path.isfile(NEW_OUTPUT_JSON):
        NEW_THRESHOLD = 0.45
        print("Applying higher threshold")
        with open(OUTPUT_JSON, "r", encoding="utf-8") as fin, open(NEW_OUTPUT_JSON, "w", encoding="utf-8") as fout:
            for line in fin:
                record = json.loads(line)
                if record.get("similarity", 0) >= NEW_THRESHOLD:
                    fout.write(json.dumps(record, ensure_ascii=False) + "\n")
        print("...Done")

    else:
        print("Extracting metadata from dump file")
        Path(OUTPUT_JSON).unlink(missing_ok=True) # just to be sure
        harvest_all_zenodo_from_dump(DUMP_PATH, RELEVANCE_QUERY, OUTPUT_JSON, MANUFACTURING_KEYWORDS)
        print("Extracting complete !")

