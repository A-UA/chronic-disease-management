from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.agent.tools.markdown_loader import load_skills_from_directory
from app.agent.tools.rag_tool import rag_search_handler

def create_agent_graph():
    # Load default tools
    SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"
    md_tools = []
    if SKILLS_DIR.exists():
        md_tools = load_skills_from_directory(str(SKILLS_DIR))
        
    tools = md_tools + [rag_search_handler]
    
    llm = ChatOpenAI(
        model=settings.CHAT_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY
    ).bind_tools(tools)
    
    # Use ToolNode for standard tool invocation fallback
    tool_node = ToolNode(tools)
    
    def assistant_node(state: MessagesState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content="你是慢病管理的 AI 助手。必须使用中文回答。")] + messages
        response = llm.invoke(messages)
        return {"messages": [response]}
        
    builder = StateGraph(MessagesState)
    builder.add_node("assistant", assistant_node)
    builder.add_node("tools", tool_node)
    
    builder.add_edge(START, "assistant")
    builder.add_conditional_edges("assistant", tools_condition)
    builder.add_edge("tools", "assistant")
    
    return builder.compile()
