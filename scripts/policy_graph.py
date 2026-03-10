from src.agents.policy_graph import export_policy_graph, export_policy_graph_dot

if __name__ == "__main__":
    json_path = export_policy_graph()
    dot_path = export_policy_graph_dot()
    print(f"Wrote policy graph to {json_path}")
    print(f"Wrote policy graph DOT to {dot_path}")
