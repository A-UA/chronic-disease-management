from app.agent.graph import create_agent_graph

def test_graph_creation():
    graph = create_agent_graph()
    assert graph is not None
    assert "assistant" in graph.nodes
    assert "tools" in graph.nodes
