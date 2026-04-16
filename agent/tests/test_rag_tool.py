from app.agent.tools.rag_tool import rag_search_handler

def test_rag_search_handler():
    # It should be a standard LangChain Tool
    assert hasattr(rag_search_handler, "name")
    assert rag_search_handler.name == "rag_search_handler"
    assert "query" in rag_search_handler.args
