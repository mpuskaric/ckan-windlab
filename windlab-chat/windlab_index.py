from ckanapi import RemoteCKAN
from sentence_transformers import SentenceTransformer
import faiss
import json
import numpy as np

CKAN_URL   = "https://windlab.hlrs.de"
INDEX_PATH = "windlab.index"
META_PATH  = "windlab_metadata.json"

model = SentenceTransformer("all-MiniLM-L6-v2")
ckan = RemoteCKAN(CKAN_URL)

print("Fetching datasets...")
result = ckan.action.package_search(rows=500)

texts = []
metadata = []

for ds in result["results"]:
    text = f"""
    Title: {ds.get('title', '')}
    Description: {ds.get('notes', '')}
    Tags: {', '.join(t['name'] for t in ds.get('tags', []))}
    Organization: {ds.get('organization', {}).get('title', '')}
    Formats: {', '.join(r.get('format', '') for r in ds.get('resources', []))}
    """
    texts.append(text.strip())

    metadata.append({
        "id": ds["id"],
        "title": ds["title"],
        "notes": ds.get("notes", ""),
        "url": f"{CKAN_URL}/dataset/{ds['name']}"
    })

print("Embedding datasets...")
embeddings = model.encode(texts, normalize_embeddings=True)

dim = embeddings.shape[1]
index = faiss.IndexFlatIP(dim)
index.add(np.array(embeddings))

faiss.write_index(index, INDEX_PATH)

with open(META_PATH, "w") as f:
    json.dump(metadata, f, indent=2)

print(f"Indexed {len(metadata)} datasets.")

