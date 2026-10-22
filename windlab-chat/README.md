# LLM Chat functionality for WindLab

This is an experimental feature that uses sentence transformers for metadata search and LLM for providing more context to the question.

Installation:
* `python3 -m venv .`
* `source bin/activate`
* `pip install -r requirements.txt`


## How to start the environment
* OLLAMA_DEBUG=1 CUDA_VISIBLE_DEVICES={GPU_ID} ollama serve (mistral:7b-instruct model)
* gunicorn app:app -k uvicorn.workers.UvicornWorker -w 4 -b 0.0.0.0:8000
* open-webui serve
