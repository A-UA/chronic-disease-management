def test_environment_initialized():
    import fastapi
    import langgraph
    import langchain_core
    assert fastapi is not None
    assert langgraph is not None
    assert langchain_core is not None
