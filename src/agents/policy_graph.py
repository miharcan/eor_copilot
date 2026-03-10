import json
from typing import Dict, List

from src.agents.retriever import load_policies


def build_policy_graph(policies) -> Dict[str, List[dict]]:
    nodes = []
    edges = []

    def add_node(node_id, node_type, label, props=None):
        nodes.append({
            "id": node_id,
            "type": node_type,
            "label": label,
            "props": props or {},
        })

    def add_edge(src, dst, rel):
        edges.append({
            "source": src,
            "target": dst,
            "relation": rel,
        })

    for policy in policies:
        doc_id = policy["doc_id"]
        country = policy.get("country")
        policy_type = policy.get("policy_type")

        add_node(
            node_id=f"doc:{doc_id}",
            node_type="policy_doc",
            label=doc_id,
            props={
                "country": country,
                "policy_type": policy_type,
                "version": policy.get("version"),
                "last_updated": policy.get("last_updated"),
            },
        )

        if country:
            add_node(
                node_id=f"country:{country}",
                node_type="country",
                label=country,
            )
            add_edge(f"country:{country}", f"doc:{doc_id}", "HAS_POLICY")

        if policy_type:
            add_node(
                node_id=f"type:{policy_type}",
                node_type="policy_type",
                label=policy_type,
            )
            add_edge(f"type:{policy_type}", f"doc:{doc_id}", "OF_TYPE")

        for section in policy["sections"]:
            section_id = section.get("section_id") or section["title"]
            node_id = f"section:{doc_id}:{section_id}"
            add_node(
                node_id=node_id,
                node_type="section",
                label=section["title"],
                props={
                    "section_id": section.get("section_id"),
                },
            )
            add_edge(f"doc:{doc_id}", node_id, "HAS_SECTION")

    return {"nodes": nodes, "edges": edges}


def export_policy_graph(path="policy_graph.json"):
    policies = load_policies()
    graph = build_policy_graph(policies)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=True)
    return path


def export_policy_graph_dot(path="policy_graph.dot"):
    policies = load_policies()
    graph = build_policy_graph(policies)

    lines = ["digraph PolicyGraph {"]
    lines.append("  rankdir=LR;")
    lines.append("  node [shape=box, fontsize=10];")

    for n in graph["nodes"]:
        label = n["label"].replace('"', "'")
        lines.append(f'  "{n["id"]}" [label="{label}"];')

    for e in graph["edges"]:
        lines.append(f'  "{e["source"]}" -> "{e["target"]}" [label="{e["relation"]}"];')

    lines.append("}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
