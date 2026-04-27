from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, trim_messages
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from app.config import settings
from app.agent.tools.markdown_loader import load_skills_from_directory
from app.agent.tools.rag_tool import rag_search_handler

# 系统级提示词，定义 AI 助手的角色、职责和回复准则
SYSTEM_PROMPT = (
    "你是慢病管理的 AI 助手。你的职责是：\n"
    "1. 帮助医护人员解答慢性病管理相关问题。\n"
    "2. 提供基于知识库的循证参考。\n"
    "3. 必须使用中文回答。\n"
    "4. 当引用知识库内容时，保留引用标记如 [1], [2]。\n"
    "5. 如果知识库中没有相关信息，诚实说明并提供通用建议。"
)

# 消息截断器：防止上下文超过 LLM Token 限制
TOKEN_TRIMMER = trim_messages(
    max_tokens=4000,
    strategy="last",          # 策略：保留最后的对话
    token_counter=len,        # Token 计数器，此处简化为字符长度近似
    include_system=True,      # 截断时保留 SystemMessage
    allow_partial=False,      # 不允许拆分单条消息
    start_on="human",         # 从人类消息开始保留
)


def create_agent_graph():
    """创建并编译 LangGraph 状态图"""
    # 定位 skills 目录以加载动态技能工具
    SKILLS_DIR = Path(__file__).parent.parent.parent / "skills"
    md_tools = []
    if SKILLS_DIR.exists():
        # 从 markdown 文件动态生成工具列表
        md_tools = load_skills_from_directory(str(SKILLS_DIR))

    # 汇总所有可用工具（动态技能 + RAG 检索工具）
    tools = md_tools + [rag_search_handler]

    # 初始化大语言模型并绑定工具
    llm = ChatOpenAI(
        model=settings.CHAT_MODEL,
        base_url=settings.LLM_BASE_URL,
        api_key=settings.LLM_API_KEY,
        stream_usage=True,  # 启用流式输出中的用量统计
    ).bind_tools(tools)

    # 预构建工具节点，负责执行 LLM 选中的工具
    tool_node = ToolNode(tools)

    async def assistant_node(state: MessagesState):
        """助手节点逻辑：处理消息、注入 Prompt 并调用 LLM"""
        messages = state["messages"]
        # 如果当前上下文没有系统提示，则在首位插入
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        # 应用 Token 截断防止溢出
        messages = TOKEN_TRIMMER.invoke(messages)
        # 调用大模型
        response = await llm.ainvoke(messages)
        # 将模型响应更新至状态中
        return {"messages": [response]}

    # 定义状态图结构
    builder = StateGraph(MessagesState)
    # 添加核心处理节点
    builder.add_node("assistant", assistant_node)
    builder.add_node("tools", tool_node)

    # 设置流程边
    builder.add_edge(START, "assistant")              # 入口：进入助手节点
    builder.add_conditional_edges("assistant", tools_condition) # 助手节点后判断：是回复用户还是调用工具
    builder.add_edge("tools", "assistant")            # 工具执行后：返回助手节点继续处理

    # 编译并返回可执行的状态图
    return builder.compile()
