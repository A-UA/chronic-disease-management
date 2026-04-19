from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, trim_messages
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.agent.tools.markdown_loader import load_skills_from_directory
from app.agent.tools.rag_tool import rag_search_handler

SYSTEM_PROMPT = (
    "你是慢病管理的 AI 助手。你的职责是：\n"
    "1. 帮助医护人员解答慢性病管理相关问题。\n"
    "2. 提供基于知识库的循证参考。\n"
    "3. 必须使用中文回答。\n"
    "4. 当引用知识库内容时，保留引用标记如 [1], [2]。\n"
    "5. 如果知识库中没有相关信息，诚实说明并提供通用建议。"
)

# Token 截断配置
TOKEN_TRIMMER = trim_messages(
    max_tokens=4000,
    strategy="last",
    token_counter=len,  # 简单字符计数近似
    include_system=True,
    allow_partial=False,
    start_on="human",
)


def create_agent_graph():
    # 加载动态技能工具
    SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"
    md_tools = []
    if SKILLS_DIR.exists():
        md_tools = load_skills_from_directory(str(SKILLS_DIR))

    tools = md_tools + [rag_search_handler]

    llm = ChatOpenAI(
        model=settings.CHAT_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
    ).bind_tools(tools)

    tool_node = ToolNode(tools)

    async def assistant_node(state: MessagesState):
        messages = state["messages"]
        # 注入系统提示
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        # Token 截断防溢出
        messages = TOKEN_TRIMMER.invoke(messages)
        response = await llm.ainvoke(messages)
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("assistant", assistant_node)
    builder.add_node("tools", tool_node)

    builder.add_edge(START, "assistant")
    builder.add_conditional_edges("assistant", tools_condition)
    builder.add_edge("tools", "assistant")

    return builder.compile()
