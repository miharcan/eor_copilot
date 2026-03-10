from src.agents.policy_graph import export_policy_graph

if __name__ == "__main__":
    path = export_policy_graph()
    print(f"Wrote policy graph to {path}")
