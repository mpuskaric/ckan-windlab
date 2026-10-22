import os
import tarfile
import json
from pathlib import Path
from lxml import etree
from tqdm import tqdm

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

import requests
import time
from urllib.parse import quote
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import DCTERMS, FOAF, RDF, XSD

import sys

# VARIABLES

BATCH_SIZE = 64
ST_THRESHOLD = 0.35

## Graph

DCAT = Namespace("http://www.w3.org/ns/dcat#")
DCT = DCTERMS
FOAF  = FOAF
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")


# Functions

def keyword_filtering(text: str, keywords) -> bool:
    text = text.lower()
    return any(stem in text for stem in keywords)

def safe_text(*items):
    return " ".join(s for s in items if isinstance(s, str))

def save_record(path, record):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def safe_uri(url: str) -> URIRef:
    return URIRef(quote(url, safe=":/#?&=%"))

# XML PARSER 

NS = {
    "oai": "http://schema.datacite.org/oai/oai-1.1/",
    "dc": "http://datacite.org/schema/kernel-4",
}

def parse_xml_record(xml_bytes):
    root = etree.fromstring(xml_bytes)
    res = root.find(".//dc:resource", namespaces=NS)
    if res is None:
        return None

    rtype = res.find(".//dc:resourceType", namespaces=NS)
    if rtype is None:
        return None

    if rtype.attrib.get("resourceTypeGeneral") != "Dataset":
        return None

    title = res.findtext(".//dc:title", namespaces=NS)
    description = res.findtext(".//dc:description", namespaces=NS)
    doi = res.findtext(".//dc:identifier[@identifierType='DOI']", namespaces=NS)

    keywords = [
        s.text for s in res.findall(".//dc:subject", namespaces=NS) if s.text
    ]

    url = res.findtext(
        ".//dc:alternateIdentifier[@alternateIdentifierType='URL']",
        namespaces=NS
    )

    return {
        "doi": doi,
        "title": title,
        "description": description,
        "keywords": keywords,
        "url": url,
    }

# HARVESTER 

def harvest_all_zenodo_from_dump(dump_path, relevance_query, output_jsonl, keywords):
    model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    query_emb = model.encode([relevance_query])

    texts, records = [], []

    with tarfile.open(dump_path, "r:gz") as tar:
        members = [m for m in tar if m.name.endswith(".xml")]

        for member in tqdm(members, desc="Scanning Zenodo dump"):
            xml_bytes = tar.extractfile(member).read()
            record = parse_xml_record(xml_bytes)
            if not record:
                continue

            text_blob = safe_text(
                record["title"],
                record["description"],
                " ".join(record["keywords"]),
            )

            if len(text_blob) < 30:
                continue

            if not keyword_filtering(text_blob, keywords):
                continue

            texts.append(text_blob)
            records.append(record)

            # --- transformer batch ---
            if len(texts) >= BATCH_SIZE:
                keep = score_and_filter(model, query_emb, texts, records)
                for r in keep:
                    save_record(output_jsonl, r)

                texts.clear()
                records.clear()

        # flush remainder
        if texts:
            keep = score_and_filter(model, query_emb, texts, records)
            for r in keep:
                save_record(output_jsonl, r)

# SCORING 

def score_and_filter(model, query_emb, texts, records):
    embs = model.encode(texts)
    sims = cosine_similarity(embs, query_emb).flatten()

    kept = []
    for score, record in zip(sims, records):
        if score >= ST_THRESHOLD:
            record["similarity"] = float(score)
            kept.append(record)

    return kept

# GRAPH

def get_record_id_from_url(url):
    return url.rstrip("/").split("/")[-1]

def fetch_record_details(record_id, zenodo_api, zenodo_token):
    headers = {}

    if zenodo_token:
        headers["Authorization"] = f"Bearer {zenodo_token}"

    r = requests.get(zenodo_api + record_id, headers=headers, timeout=30)
    if r.status_code != 200:
        return []

    data = r.json()

    files     = data.get("files", [])
    metadata  = data.get("metadata", [])
    creators  = metadata.get("creators",[])
    licenses  = metadata.get("license",[])
    #issued   = metadata.get("publication_date",[])
    issued    = data.get("created",[])
    modified  = data.get("modified",[])

    print(metadata)

    '''
    distributions = []
    for f in files:
        distributions.append({
            "title": f.get("key"),
            "url": f.get("links", {}).get("self")
        })

    #time.sleep(0.67)
    '''
    return creators, files, licenses, issued, modified

def build_graph(updated_jsonl, zenodo_api, zenodo_token):
    g = Graph()
    g.bind("dcat", DCAT)
    g.bind("dct", DCT)
    g.bind("foaf", FOAF)

    # Catalog
    catalog_uri = URIRef("https://zenodo.org/catalog/manufacturing-ai")
    g.add((catalog_uri, RDF.type, DCAT.Catalog))
    g.add((catalog_uri, DCT.title,
           Literal("Zenodo AI-Relevant Manufacturing Datasets", lang="en")))
    g.add((catalog_uri, DCT.description,
           Literal("AI-filtered manufacturing datasets from Zenodo", lang="en")))

    with open(updated_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)

            doi = record["doi"]
            dataset_uri = URIRef(f"https://doi.org/{doi}")

            record_id = get_record_id_from_url(record["url"])
            creators, files, licenses, issued, modified = fetch_record_details(record_id, zenodo_api, zenodo_token)

            # license:
            if licenses:
                license_id = licenses['id']
            else:
                license_id = ''

            g.add((dataset_uri, RDF.type, DCAT.Dataset))
            g.add((catalog_uri, DCAT.dataset, dataset_uri))

            g.add((dataset_uri, DCT.identifier, Literal(doi)))

            # Title
            if record.get("title"):
                g.add((dataset_uri, DCT.title,
                       Literal(record["title"], lang="en")))
            
            # Description
            if record.get("description"):
                g.add((dataset_uri, DCT.description,
                       Literal(record["description"], lang="en")))
            
            # Keywords
            for kw in record.get("keywords", []) + ["public"]:
                g.add((dataset_uri, DCAT.keyword,
                       Literal(kw, lang="en")))

            # Issued
            g.add((dataset_uri, DCT.issued, Literal(issued, datatype=XSD.date)))

            # Modified
            g.add((dataset_uri, DCT.modified, Literal(modified, datatype=XSD.date)))

            # Creators
            for creator in creators:
                name = creator.get("name")
                if name:
                    creator_uri = URIRef(
                        f"https://zenodo.org/author/{name.replace(' ', '_')}"
                    )
                    g.add((creator_uri, RDF.type, FOAF.Person))
                    g.add((creator_uri, FOAF.name, Literal(name)))
                    g.add((dataset_uri, DCT.creator, creator_uri))

            #Publisher
            print(publisher)
            if publisher:
                g.add((dataset_uri, DCT.publisher, Literal(publisher)))

            # Distributions
            for f in files:
                #file_uri = URIRef(f["links"]["self"])
                file_uri    = safe_uri(f["links"]["self"])
                g.add((file_uri, RDF.type, DCAT.Distribution))
                g.add((file_uri, DCT.title, Literal(f["key"])))
                g.add((file_uri, DCAT.accessURL, file_uri))
                g.add((file_uri, DCT.license, Literal(license_id)))
                g.add((dataset_uri, DCAT.distribution, file_uri))

    return g

