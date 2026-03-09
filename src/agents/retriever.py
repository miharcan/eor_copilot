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


def _is_stale(policy, all_policies):
    doc_id = policy["doc_id"]

    if "_v" not in doc_id:
        return False

    base, version = doc_id.rsplit("_v", 1)
    version = int(version)

    for p in all_policies:
        other = p["doc_id"]

        if other.startswith(base + "_v"):
            other_version = int(other.rsplit("_v", 1)[1])

            if other_version > version:
                return True

    return False


def _latest_by_doc_id(policies):
    latest = {}

    for policy in policies:
        doc_id = policy["doc_id"]

        base = doc_id.split("_v")[0]
        version = int(doc_id.split("_v")[1])

        if base not in latest or version > latest[base]["_version"]:
            policy["_version"] = version
            latest[base] = policy

    return list(latest.values())


def build_embeddings(policies):
    sections = []
    metadata = []

    for policy in policies:
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
                "stale": _is_stale(policy, policies)
            })

    embeddings = model.encode(sections, normalize_embeddings=True)
    return sections, metadata, embeddings


POLICIES = _latest_by_doc_id(load_policies())
SECTIONS, METADATA, DOC_EMBEDDINGS = build_embeddings(POLICIES)
TOKENIZED_SECTIONS = [re.sub(r"\W", " ", s.lower()).split() for s in SECTIONS]
BM25 = BM25Okapi(TOKENIZED_SECTIONS)


def retrieve(query):
    query_lower = re.sub(r"\W", " ", query.lower())
    query_tokens = query_lower.split()

    country_filtered_indices = [
        i for i, m in enumerate(METADATA)
        if m["country"] and m["country"].lower() in query_lower
    ]

    if not country_filtered_indices:
        return []

    bm25_scores = BM25.get_scores(query_tokens)
    query_embedding = model.encode([query], normalize_embeddings=True)[0]
    dense_scores = DOC_EMBEDDINGS @ query_embedding

    bm25_scores = bm25_scores / (np.max(bm25_scores) + 1e-6)
    dense_scores = dense_scores / (np.max(dense_scores) + 1e-6)
    hybrid_scores = 0.5 * bm25_scores + 0.5 * dense_scores

    ranked = sorted(
        country_filtered_indices,
        key=lambda i: hybrid_scores[i],
        reverse=True
    )[:3]

    return [METADATA[i] for i in ranked if hybrid_scores[i] > 0.2]
