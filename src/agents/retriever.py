import json
import os
import re
from datetime import date
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

POLICY_DIR = "data/policies"
STALE_DAYS_THRESHOLD = 365

model = SentenceTransformer("all-MiniLM-L6-v2")

def load_policies():
    policies = []
    for f in os.listdir(POLICY_DIR):
        if f.endswith(".json"):
            with open(os.path.join(POLICY_DIR, f)) as file:
                policies.append(json.load(file))
    return policies

def _parse_date(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None

def _is_stale(last_updated):
    updated = _parse_date(last_updated)
    if not updated:
        return False
    return (date.today() - updated).days > STALE_DAYS_THRESHOLD

def _latest_by_doc_id(policies):
    latest = {}
    for policy in policies:
        doc_id = policy.get("doc_id")
        version = policy.get("version", 0)
        if doc_id not in latest:
            latest[doc_id] = policy
            continue
        current = latest[doc_id]
        current_version = current.get("version", 0)
        if version > current_version:
            latest[doc_id] = policy
    return list(latest.values())

def retrieve(query):
    policies = _latest_by_doc_id(load_policies())
    results = []

    query_lower = re.sub(r"\W", " ", query.lower())
    query_tokens = query_lower.split()

    sections = []
    metadata = []
    for policy in policies:

        country_match = policy["country"].lower() in query_lower

        if not country_match:
            continue

        for section in policy["sections"]:
            text = section["text"]

            sections.append(text)

            metadata.append({
                "doc_id": policy["doc_id"],
                "section": section["title"],
                "text": text,
                "timestamp": policy["last_updated"],
                "version": policy.get("version"),
                "country": policy.get("country"),
                "policy_type": policy.get("policy_type"),
                "stale": _is_stale(policy.get("last_updated"))
            })

    if not sections:
        return []

    # BM25 lexical retrieval
    tokenized_sections = [re.sub(r"\W", " ", s.lower()).split() for s in sections]
    bm25 = BM25Okapi(tokenized_sections)
    bm25_scores = bm25.get_scores(query_tokens)

    # Dense retrieval: normalize embeddings so dot product == cosine similarity
    doc_embeddings = model.encode(sections, normalize_embeddings=True)
    query_embedding = model.encode([query], normalize_embeddings=True)[0]
    dense_scores = doc_embeddings @ query_embedding

    # normalize scores
    bm25_scores = bm25_scores / (np.max(bm25_scores) + 1e-6)
    dense_scores = dense_scores / (np.max(dense_scores) + 1e-6)

    hybrid_scores = 0.5 * bm25_scores + 0.5 * dense_scores

    top_indices = np.argsort(hybrid_scores)[::-1][:3]

    for idx in top_indices:
        if hybrid_scores[idx] > 0.2:   # small relevance threshold
            results.append(metadata[idx])

    return results
