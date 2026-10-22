# app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import requests
import json
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# ---------------- Config ----------------
INDEX_PATH = "ckan.index"          # FAISS index of CKAN dataset embeddings
META_PATH = "metadata.json"        # CKAN dataset metadata
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "mistral:7b-instruct"
TOP_K_DEFAULT = 5

# ---------------- App ----------------
app = FastAPI(title="CKAN RAG OpenAI-compatible API")

# Enable CORS for Open WebUI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Load models ----------------
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
index = faiss.read_index(INDEX_PATH)
with open(META_PATH) as f:
    metadata = json.load(f)

# ---------------- OpenAI-compatible models ----------------
class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]

# ---------------- Helper functions ----------------
def retrieve(question: str, top_k: int = TOP_K_DEFAULT):
    """Retrieve top-K datasets from CKAN using FAISS + embeddings."""
    q_emb = embedding_model.encode([question], normalize_embeddings=True)
    scores, indices = index.search(np.array(q_emb), top_k)
    results = []
    for i, idx in enumerate(indices[0]):
        ds = metadata[idx]
        results.append({
            "rank": i + 1,
            "score": float(scores[0][i]),
            "title": ds["title"],
            "description": ds.get("notes", "")[:500],
            "url": ds.get("url", "")
        })
    return results

def ollama_explain_filtered(question: str, datasets: list):

    first_prompt = f"""
You are a routing system for a WindLab Knowledge and Data Hub.
Classify the user question into exactly ONE category:
1. "general"
- greetings, identity questions, chit-chat, help about the assistant

2. "catalog"
- user wants datasets about a topic (wind energy, airborne, turbine, wind farms, measurements, etc.)

3. "system"
- questions about the CKAN portal itself
- examples: 
    - how many datasets exist
    - what datasets are hosted
    - what is this platform
    - statistics about the catalog

Return ONLY one word: general, catalog or system.

Question:
{question}
"""

    r = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": first_prompt, "stream": False},
        timeout=60
    )

    route = r.json()["response"].strip().lower()

    if route == "general":
        general_prompt = f"""
You are a helpful assistant for a WindLab Knowledge and Data Hub hosting datasets related to wind energy research. WindLab is created by three european Horizon projects: MERIDIONAL, FLOW and AIRE. 

You can:
- explain who you are
- help users understand the portal
- guide users on how to find datasets

User question:
{question}

Respond naturally and clearly.
"""
        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": general_prompt, "stream": False},
            timeout=60
        )

        answer = r.json()["response"].strip()
        return "Explanation:\n" + answer, []

    if route == "system":
        system_prompt = f"""
You are a helpful assistant for a WindLab Knowledge and Data Hub hosting datasets related to wind energy research. WindLab is created by three european Horizon projects: MERIDIONAL, FLOW and AIRE. 
You answer questions about the WindLab itself

If the question asks for counts of data or organizations, you can say that WindLab hosts ca 1200 datasets and has 27 organizations. 

User question:
{question}

Respond clearly and concisely.
"""

        r = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": system_prompt, "stream": False},
            timeout=60
        )

        answer = r.json()["response"].strip()
        return "Explanation:\n" + answer, []

    
    context = ""
    for i, ds in enumerate(datasets, 1):
        context += f"{i}. Title: {ds['title']}\n"
        context += f"   Description: {ds['description']}\n"
        context += f"   URL: {ds['url']}\n"

    prompt = f"""
You are a data catalog assistant for the WindLab Knowledge and Data Hub, which supports wind energy research 
Your job is to help users find datasets relevant to their question.

Rules:
- Only use the datasets provided below
- If none are relevant, say "There are no datasets"
- Otherwise, list only relevant datasets
- Provide an explanation for each relevant dataset

User question:
{question}

Available datasets:
{context}
"""

    r = requests.post(
        OLLAMA_URL,
        json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=120
    )
    explanation = r.json()["response"]

    print("STATUS:", r.status_code)
    print("TEXT:", r.text)

    # Detect if Ollama said NONE
    if "NO_DATASETS" in explanation.upper() or "no datasets" in explanation.lower():
        explanation_text = "Explanation:\nThere are no datasets are relevant to your question."
        return explanation_text, []

    explanation_text = "Explanation:\n" + explanation.strip()
    return explanation_text, datasets

# ---------------- Endpoints ----------------
@app.get("/v1/models")
def list_models():
    """OpenAI-compatible endpoint for listing models."""
    return {"data": [{"id": "windlab-rag", "object": "model"}]}

@app.post("/v1/chat/completions")
def chat_completion(req: ChatCompletionRequest):
    """OpenAI-compatible chat endpoint with CKAN RAG + Ollama explain."""
    # Extract last user message
    user_msg = next(m.content for m in reversed(req.messages) if m.role == "user")

    # Step 1: Retrieve top datasets
    top_datasets = retrieve(user_msg, top_k=TOP_K_DEFAULT)

    # Step 2: Ask Ollama to filter & explain
    explanation, relevant_datasets = ollama_explain_filtered(user_msg, top_datasets)

    # Step 3: Build Markdown response only for relevant datasets
    response_text = explanation + "\n\n"
    if relevant_datasets:
        response_text += "**Relevant Datasets:**\n"
        for r in relevant_datasets:
            response_text += f"**{r['title']}**\n{r['description']}\n[Link]({r['url']})\n\n"

    return {"choices": [{"message": {"role": "assistant", "content": response_text}}]}

