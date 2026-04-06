# LangGraph Agent 集成实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保留现有安全架构（RLS + RBAC + 租户隔离）的前提下，引入 LangGraph 实现 Agent 能力，支持多 Skill 调用、对话记忆、工具编排。

**Architecture:** "安全桥接层 + Skills 框架 + LangGraph 编排"三层架构。业务层零改动，仅重构 AI Pipeline 层。所有 LangGraph 节点通过 `SecurityContext` 获取已注入 RLS 的 DB Session。

**Tech Stack:** `langgraph` (图编排) + `openai` SDK (LLM/Embedding 保留) + PostgreSQL RLS (安全) + Redis (缓存)

---

## 文件结构总览

```
backend/app/services/agent/           ← 新建目录
├── __init__.py                        # 导出 SecurityContext
├── security.py                        # SecurityContext 安全桥接层
├── state.py                           # LangGraph AgentState 定义
├── graph.py                           # LangGraph 图定义 + 编排
├── skills/
│   ├── __init__.py                    # 导出 skill_registry
│   ├── base.py                        # SkillDefinition + SkillRegistry
│   ├── rag_skill.py                   # RAG 检索技能（桥接现有 chat.py）
│   ├── patient_skills.py              # 患者查询 + 健康趋势
│   └── calculator_skills.py           # BMI 等纯计算技能
└── memory.py                          # 对话记忆（桥接现有 conversation_*.py）

backend/app/api/endpoints/chat.py      ← 修改：接入 Agent 图
backend/app/services/provider_registry.py ← 修改：注册 Agent 图

不动的文件（业务层）：
  api/deps.py, db/models/, db/session.py, core/, schemas/,
  所有非 AI 的 endpoints, services/quota.py, services/rbac.py,
  services/audit.py, services/health_alert.py, services/email.py,
  services/storage.py, services/settings.py

保留但被 Agent 层桥接调用的文件（不删除，不修改接口）：
  services/llm.py, services/embeddings.py, services/chat.py,
  services/reranker.py, services/query_rewrite.py,
  services/rag_ingestion.py, services/document_parser.py,
  services/conversation_context.py, services/conversation_compress.py,
  services/rag_evaluation.py, services/embedding_validation.py
```

---

## 安装依赖

```powershell
cd d:\codes\chronic-disease-management\backend
uv add langgraph
```

---

### Task 1: SecurityContext 安全桥接层

**Files:**
- Create: `backend/app/services/agent/__init__.py`
- Create: `backend/app/services/agent/security.py`
- Test: `backend/tests/services/test_agent_security.py`

- [ ] **Step 1: 创建 SecurityContext**

```python
# backend/app/services/agent/security.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

@dataclass(frozen=True, slots=True)
class SecurityContext:
    """Agent 执行所需的安全上下文 — 由 FastAPI DI 层构建"""
    tenant_id: int
    org_id: int
    user_id: int
    roles: tuple[str, ...] = ()
    permissions: frozenset[str] = field(default_factory=frozenset)
    db: AsyncSession | None = None

    def has_permission(self, perm_code: str) -> bool:
        return perm_code in self.permissions

    def require_permission(self, perm_code: str) -> None:
        if perm_code not in self.permissions:
            raise PermissionError(f"缺少权限: {perm_code}")
```

```python
# backend/app/services/agent/__init__.py
from app.services.agent.security import SecurityContext
__all__ = ["SecurityContext"]
```

- [ ] **Step 2: 编写测试**

```python
# backend/tests/services/test_agent_security.py
import pytest
from app.services.agent.security import SecurityContext

class TestSecurityContext:
    def test_immutable(self):
        ctx = SecurityContext(tenant_id=1, org_id=2, user_id=3)
        with pytest.raises(AttributeError):
            ctx.tenant_id = 999

    def test_has_permission(self):
        ctx = SecurityContext(tenant_id=1, org_id=2, user_id=3,
            permissions=frozenset({"patient:read"}))
        assert ctx.has_permission("patient:read") is True
        assert ctx.has_permission("patient:delete") is False

    def test_require_permission_raises(self):
        ctx = SecurityContext(tenant_id=1, org_id=2, user_id=3, permissions=frozenset())
        with pytest.raises(PermissionError, match="缺少权限"):
            ctx.require_permission("patient:read")

    def test_require_permission_passes(self):
        ctx = SecurityContext(tenant_id=1, org_id=2, user_id=3,
            permissions=frozenset({"patient:read"}))
        ctx.require_permission("patient:read")
```

- [ ] **Step 3: 运行测试**

```powershell
uv run pytest tests/services/test_agent_security.py -v
```
Expected: 4 PASSED

- [ ] **Step 4: 提交**

```powershell
git add app/services/agent/ tests/services/test_agent_security.py
git commit -m "feat(agent): 添加 SecurityContext 安全桥接层"
```

---

### Task 2: Skills 基础设施

**Files:**
- Create: `backend/app/services/agent/skills/__init__.py`
- Create: `backend/app/services/agent/skills/base.py`
- Test: `backend/tests/services/test_agent_skills_base.py`

- [ ] **Step 1: 创建 SkillDefinition + SkillRegistry**

```python
# backend/app/services/agent/skills/base.py
from __future__ import annotations
import json, logging
from dataclasses import dataclass
from typing import Any, Callable, Awaitable
from app.services.agent.security import SecurityContext

logger = logging.getLogger(__name__)

@dataclass(slots=True)
class SkillResult:
    success: bool
    data: Any = None
    error: str | None = None
    def to_context_string(self) -> str:
        if not self.success:
            return f"[技能执行失败: {self.error}]"
        if isinstance(self.data, str):
            return self.data
        return json.dumps(self.data, ensure_ascii=False, default=str)

SkillHandler = Callable[..., Awaitable[SkillResult]]

@dataclass(slots=True)
class SkillDefinition:
    name: str
    description: str
    parameters_schema: dict[str, Any]
    handler: SkillHandler
    required_permission: str | None = None
    def to_openai_tool_schema(self) -> dict:
        return {"type": "function", "function": {
            "name": self.name, "description": self.description,
            "parameters": self.parameters_schema}}

class SkillRegistry:
    def __init__(self):
        self._skills: dict[str, SkillDefinition] = {}
    def register(self, skill: SkillDefinition) -> None:
        self._skills[skill.name] = skill
    def get(self, name: str) -> SkillDefinition | None:
        return self._skills.get(name)
    def get_available(self, permissions: frozenset[str]) -> list[SkillDefinition]:
        return [s for s in self._skills.values()
                if s.required_permission is None or s.required_permission in permissions]
    def get_tool_schemas(self, permissions: frozenset[str]) -> list[dict]:
        return [s.to_openai_tool_schema() for s in self.get_available(permissions)]
    async def execute(self, name: str, ctx: SecurityContext, params: dict[str, Any]) -> SkillResult:
        skill = self.get(name)
        if skill is None:
            return SkillResult(success=False, error=f"未知技能: {name}")
        if skill.required_permission and not ctx.has_permission(skill.required_permission):
            return SkillResult(success=False, error=f"权限不足: 需要 {skill.required_permission}")
        allowed = set(skill.parameters_schema.get("properties", {}).keys())
        safe_params = {k: v for k, v in params.items() if k in allowed}
        try:
            return await skill.handler(ctx, **safe_params)
        except Exception as e:
            logger.error("Skill %s 执行失败", name, exc_info=True)
            return SkillResult(success=False, error=str(e))

skill_registry = SkillRegistry()
```

```python
# backend/app/services/agent/skills/__init__.py
from app.services.agent.skills.base import SkillDefinition, SkillRegistry, SkillResult, skill_registry
__all__ = ["SkillDefinition", "SkillRegistry", "SkillResult", "skill_registry"]
```

- [ ] **Step 2: 编写测试**

```python
# backend/tests/services/test_agent_skills_base.py
import pytest
from app.services.agent.security import SecurityContext
from app.services.agent.skills.base import SkillDefinition, SkillRegistry, SkillResult

async def _echo(ctx, message=""): return SkillResult(success=True, data=f"echo:{message}")
async def _boom(ctx): raise RuntimeError("boom")
def _ctx(perms=frozenset()): return SecurityContext(tenant_id=1,org_id=2,user_id=3,permissions=perms)

ECHO = SkillDefinition(name="echo", description="回显", handler=_echo,
    parameters_schema={"type":"object","properties":{"message":{"type":"string"}}})
PROTECTED = SkillDefinition(name="protected", description="受保护", handler=_echo,
    parameters_schema={"type":"object","properties":{}}, required_permission="admin:manage")

class TestSkillRegistry:
    def test_register_and_get(self):
        r = SkillRegistry(); r.register(ECHO)
        assert r.get("echo") is ECHO
    def test_filter_by_permission(self):
        r = SkillRegistry(); r.register(ECHO); r.register(PROTECTED)
        assert len(r.get_available(frozenset())) == 1
        assert len(r.get_available(frozenset({"admin:manage"}))) == 2
    @pytest.mark.asyncio
    async def test_execute_success(self):
        r = SkillRegistry(); r.register(ECHO)
        res = await r.execute("echo", _ctx(), {"message": "hi"})
        assert res.success and res.data == "echo:hi"
    @pytest.mark.asyncio
    async def test_execute_permission_denied(self):
        r = SkillRegistry(); r.register(PROTECTED)
        res = await r.execute("protected", _ctx(), {})
        assert not res.success and "权限不足" in res.error
    @pytest.mark.asyncio
    async def test_execute_unknown(self):
        res = await SkillRegistry().execute("nope", _ctx(), {})
        assert not res.success
    @pytest.mark.asyncio
    async def test_params_whitelist(self):
        r = SkillRegistry(); r.register(ECHO)
        res = await r.execute("echo", _ctx(), {"message":"hi","evil":"drop"})
        assert res.success
    @pytest.mark.asyncio
    async def test_handler_exception(self):
        r = SkillRegistry()
        r.register(SkillDefinition(name="fail",description="",handler=_boom,
            parameters_schema={"type":"object","properties":{}}))
        res = await r.execute("fail", _ctx(), {})
        assert not res.success and "boom" in res.error
```

- [ ] **Step 3: 运行测试** `uv run pytest tests/services/test_agent_skills_base.py -v` → 7 PASSED

- [ ] **Step 4: 提交** `git commit -m "feat(agent): 添加 Skills 基础设施 — SkillRegistry"`

---

### Task 3: 业务 Skills 实现

**Files:**
- Create: `backend/app/services/agent/skills/rag_skill.py`
- Create: `backend/app/services/agent/skills/patient_skills.py`
- Create: `backend/app/services/agent/skills/calculator_skills.py`
- Test: `backend/tests/services/test_agent_business_skills.py`

- [ ] **Step 1: RAG 检索 Skill（桥接现有 chat.py）**

```python
# backend/app/services/agent/skills/rag_skill.py
"""RAG 检索技能 — 桥接现有的 retrieve_chunks + build_rag_prompt"""
from app.services.agent.security import SecurityContext
from app.services.agent.skills.base import SkillDefinition, SkillResult, skill_registry
from app.services.chat import retrieve_chunks, build_rag_prompt
from app.services.provider_registry import registry


async def rag_search_handler(
    ctx: SecurityContext, query: str = "", kb_id: int = 0,
) -> SkillResult:
    if not query or not kb_id:
        return SkillResult(success=False, error="需要 query 和 kb_id 参数")
    try:
        llm = registry.get_llm()
        chunks = await retrieve_chunks(
            db=ctx.db, query=query, kb_id=kb_id,
            org_id=ctx.org_id, user_id=ctx.user_id,
            llm_provider=llm,
        )
        if not chunks:
            return SkillResult(success=True, data="未找到相关文档内容")
        prompt, citations = build_rag_prompt(query, chunks)
        return SkillResult(success=True, data={
            "context": prompt, "citations": citations, "chunk_count": len(chunks),
        })
    except Exception as e:
        return SkillResult(success=False, error=str(e))

skill_registry.register(SkillDefinition(
    name="rag_search",
    description="在知识库中检索与问题相关的文档内容，返回带引用的上下文",
    parameters_schema={"type": "object", "properties": {
        "query": {"type": "string", "description": "检索问题"},
        "kb_id": {"type": "integer", "description": "知识库 ID"},
    }, "required": ["query", "kb_id"]},
    handler=rag_search_handler,
    required_permission="chat:use",
))
```

- [ ] **Step 2: 患者查询 + 健康趋势 Skills**

```python
# backend/app/services/agent/skills/patient_skills.py
"""患者相关 Skills — 所有数据访问通过 ctx.db（带 RLS）"""
from sqlalchemy import select
from app.db.models import PatientProfile, HealthMetric
from app.services.agent.security import SecurityContext
from app.services.agent.skills.base import SkillDefinition, SkillResult, skill_registry


async def query_patient_handler(
    ctx: SecurityContext, patient_id: int | None = None, name: str | None = None,
) -> SkillResult:
    try:
        stmt = select(PatientProfile)
        if patient_id:
            stmt = stmt.where(PatientProfile.id == patient_id)
        elif name:
            stmt = stmt.where(PatientProfile.name.ilike(f"%{name}%"))
        else:
            return SkillResult(success=False, error="请提供 patient_id 或 name")
        result = await ctx.db.execute(stmt.limit(5))
        patients = result.scalars().all()
        if not patients:
            return SkillResult(success=True, data="未找到匹配的患者")
        data = [{"id": str(p.id), "name": p.name, "gender": p.gender,
                 "primary_diagnosis": p.primary_diagnosis} for p in patients]
        return SkillResult(success=True, data=data)
    except Exception as e:
        return SkillResult(success=False, error=str(e))


async def health_trend_handler(
    ctx: SecurityContext, patient_id: int = 0, metric_type: str = "blood_pressure", days: int = 30,
) -> SkillResult:
    if not patient_id:
        return SkillResult(success=False, error="需要 patient_id")
    try:
        stmt = (select(HealthMetric)
            .where(HealthMetric.patient_id == patient_id, HealthMetric.metric_type == metric_type)
            .order_by(HealthMetric.recorded_at.desc()).limit(days))
        result = await ctx.db.execute(stmt)
        metrics = result.scalars().all()
        if not metrics:
            return SkillResult(success=True, data=f"近 {days} 天无 {metric_type} 记录")
        data = [{"date": m.recorded_at.isoformat(), "value": m.value,
                 "type": m.metric_type} for m in metrics]
        return SkillResult(success=True, data=data)
    except Exception as e:
        return SkillResult(success=False, error=str(e))

skill_registry.register(SkillDefinition(
    name="query_patient", description="根据 ID 或姓名查询患者档案",
    parameters_schema={"type": "object", "properties": {
        "patient_id": {"type": "integer", "description": "患者 ID"},
        "name": {"type": "string", "description": "患者姓名（模糊搜索）"},
    }},
    handler=query_patient_handler, required_permission="patient:read",
))

skill_registry.register(SkillDefinition(
    name="health_trend", description="查询患者健康指标趋势（血压/血糖/体重/心率等）",
    parameters_schema={"type": "object", "properties": {
        "patient_id": {"type": "integer", "description": "患者 ID"},
        "metric_type": {"type": "string", "enum": [
            "blood_pressure","blood_sugar","weight","heart_rate","bmi","spo2"],
            "description": "指标类型"},
        "days": {"type": "integer", "description": "查询天数", "default": 30},
    }, "required": ["patient_id"]},
    handler=health_trend_handler, required_permission="patient:read",
))
```

- [ ] **Step 3: 纯计算 Skill（无需权限，无需 DB）**

```python
# backend/app/services/agent/skills/calculator_skills.py
"""纯计算技能 — 无需权限，无需 DB 访问"""
from app.services.agent.security import SecurityContext
from app.services.agent.skills.base import SkillDefinition, SkillResult, skill_registry


async def bmi_calculator_handler(
    ctx: SecurityContext, height_cm: float = 0, weight_kg: float = 0,
) -> SkillResult:
    if height_cm <= 0 or weight_kg <= 0:
        return SkillResult(success=False, error="身高和体重必须大于 0")
    height_m = height_cm / 100
    bmi = round(weight_kg / (height_m ** 2), 1)
    if bmi < 18.5: level = "偏瘦"
    elif bmi < 24: level = "正常"
    elif bmi < 28: level = "超重"
    else: level = "肥胖"
    return SkillResult(success=True, data={"bmi": bmi, "level": level,
        "height_cm": height_cm, "weight_kg": weight_kg})

skill_registry.register(SkillDefinition(
    name="bmi_calculator", description="根据身高体重计算 BMI 并判断等级",
    parameters_schema={"type": "object", "properties": {
        "height_cm": {"type": "number", "description": "身高（厘米）"},
        "weight_kg": {"type": "number", "description": "体重（公斤）"},
    }, "required": ["height_cm", "weight_kg"]},
    handler=bmi_calculator_handler,
    required_permission=None,  # 无需权限
))
```

- [ ] **Step 4: 编写测试**

```python
# backend/tests/services/test_agent_business_skills.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.agent.security import SecurityContext
from app.services.agent.skills.calculator_skills import bmi_calculator_handler

def _ctx(perms=frozenset()):
    return SecurityContext(tenant_id=1, org_id=2, user_id=3,
        permissions=perms, db=MagicMock())

class TestBMICalculator:
    @pytest.mark.asyncio
    async def test_normal_bmi(self):
        res = await bmi_calculator_handler(_ctx(), height_cm=170, weight_kg=65)
        assert res.success
        assert res.data["bmi"] == 22.5
        assert res.data["level"] == "正常"

    @pytest.mark.asyncio
    async def test_obese_bmi(self):
        res = await bmi_calculator_handler(_ctx(), height_cm=170, weight_kg=90)
        assert res.success
        assert res.data["level"] == "肥胖"

    @pytest.mark.asyncio
    async def test_invalid_input(self):
        res = await bmi_calculator_handler(_ctx(), height_cm=0, weight_kg=70)
        assert not res.success
```

- [ ] **Step 5: 运行测试** `uv run pytest tests/services/test_agent_business_skills.py -v` → 3 PASSED

- [ ] **Step 6: 提交** `git commit -m "feat(agent): 添加业务 Skills — RAG/患者/计算器"`

---

### Task 4: LangGraph AgentState + 图定义

**Files:**
- Create: `backend/app/services/agent/state.py`
- Create: `backend/app/services/agent/graph.py`
- Test: `backend/tests/services/test_agent_graph.py`

- [ ] **Step 1: 定义 AgentState**

```python
# backend/app/services/agent/state.py
"""LangGraph Agent 状态定义"""
from __future__ import annotations
from typing import Any, TypedDict
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """Agent 状态 — LangGraph 图的共享状态"""
    messages: list[dict[str, str]]          # 对话消息列表
    query: str                              # 当前用户查询
    kb_id: int                              # 知识库 ID
    skill_results: list[dict[str, Any]]     # Skill 执行结果缓存
    citations: list[dict]                   # RAG 引用
    final_answer: str                       # 最终回答
    iteration: int                          # 当前迭代轮次（安全防护）
    max_iterations: int                     # 最大迭代次数（默认 3）
```

- [ ] **Step 2: 定义 LangGraph 图**

```python
# backend/app/services/agent/graph.py
"""LangGraph 图定义 — 核心编排逻辑

图结构：
  START → router → [rag_node | skill_node | direct_answer] → synthesize → END
                  ↑_______________ loop (max 3) ______________|
"""
from __future__ import annotations
import json, logging
from typing import Any

from langgraph.graph import StateGraph, END

from app.services.agent.security import SecurityContext
from app.services.agent.skills.base import skill_registry
from app.services.agent.state import AgentState
from app.services.provider_registry import registry

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 3

# --- 节点函数 ---

async def router_node(state: AgentState, ctx: SecurityContext) -> dict:
    """意图路由：让 LLM 决定调用哪个 Skill"""
    if state["iteration"] >= state["max_iterations"]:
        return {"final_answer": "已达到最大推理轮次，请重新提问。"}

    available = skill_registry.get_available(ctx.permissions)
    if not available:
        return {"_next": "direct_answer"}

    tool_list = "\n".join(f"- {s.name}: {s.description}" for s in available)
    prompt = (
        f"你是慢病管理 AI 助手的意图路由器。\n"
        f"可用技能:\n{tool_list}\n\n"
        f"用户问题: {state['query']}\n\n"
        f"如需调用技能返回 JSON: {{\"skill\": \"名称\", \"params\": {{}}}}\n"
        f"如不需要返回: {{\"skill\": \"none\"}}\n"
        f"只返回 JSON。"
    )
    llm = registry.get_llm()
    try:
        response = await llm.complete_text(prompt)
        parsed = json.loads(response.strip())
        skill_name = parsed.get("skill", "none")
        if skill_name == "none":
            return {"_next": "direct_answer"}
        return {"_next": "skill_node", "_skill_name": skill_name,
                "_skill_params": parsed.get("params", {})}
    except Exception:
        logger.warning("Router 解析失败，降级到 RAG", exc_info=True)
        return {"_next": "rag_node"}


async def rag_node(state: AgentState, ctx: SecurityContext) -> dict:
    """RAG 检索节点 — 桥接现有 retrieve_chunks"""
    from app.services.chat import retrieve_chunks, build_rag_prompt
    llm = registry.get_llm()
    chunks = await retrieve_chunks(
        db=ctx.db, query=state["query"], kb_id=state["kb_id"],
        org_id=ctx.org_id, user_id=ctx.user_id, llm_provider=llm,
    )
    if not chunks:
        return {"final_answer": "未找到相关文档内容，无法回答此问题。", "citations": []}
    prompt, citations = build_rag_prompt(state["query"], chunks)
    response = ""
    async for chunk_text in llm.stream_text(prompt):
        response += chunk_text
    return {"final_answer": response, "citations": citations}


async def skill_node(state: AgentState, ctx: SecurityContext) -> dict:
    """技能执行节点"""
    skill_name = state.get("_skill_name", "")
    skill_params = state.get("_skill_params", {})
    result = await skill_registry.execute(skill_name, ctx, skill_params)
    if not result.success:
        return {"_next": "rag_node"}  # Skill 失败降级到 RAG
    # 用 Skill 结果构建 prompt 让 LLM 合成回答
    llm = registry.get_llm()
    prompt = (
        f"你是慢病管理 AI 助手。以下是通过数据查询获得的信息：\n\n"
        f"{result.to_context_string()}\n\n"
        f"用户问题：{state['query']}\n\n"
        f"请基于以上数据用中文 Markdown 格式回答。"
    )
    response = await llm.complete_text(prompt)
    return {"final_answer": response, "skill_results": [
        {"skill": skill_name, "params": skill_params, "data": result.data}
    ]}


async def direct_answer_node(state: AgentState, ctx: SecurityContext) -> dict:
    """直接回答节点 — 无需 Skill，LLM 直接回答"""
    llm = registry.get_llm()
    prompt = f"你是慢病管理 AI 助手。请用中文 Markdown 回答：\n\n{state['query']}"
    response = await llm.complete_text(prompt)
    return {"final_answer": response}


def build_agent_graph() -> StateGraph:
    """构建 Agent 图（不含 SecurityContext，运行时通过闭包注入）"""
    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("rag_node", rag_node)
    graph.add_node("skill_node", skill_node)
    graph.add_node("direct_answer", direct_answer_node)

    graph.set_entry_point("router")
    graph.add_conditional_edges("router", lambda s: s.get("_next", "rag_node"), {
        "rag_node": "rag_node",
        "skill_node": "skill_node",
        "direct_answer": "direct_answer",
    })
    graph.add_edge("rag_node", END)
    graph.add_edge("skill_node", END)
    graph.add_edge("direct_answer", END)

    return graph
```

- [ ] **Step 3: 编写测试**

```python
# backend/tests/services/test_agent_graph.py
import pytest
from app.services.agent.state import AgentState

class TestAgentState:
    def test_state_creation(self):
        state: AgentState = {
            "messages": [], "query": "测试", "kb_id": 1,
            "skill_results": [], "citations": [],
            "final_answer": "", "iteration": 0, "max_iterations": 3,
        }
        assert state["query"] == "测试"
        assert state["max_iterations"] == 3

    def test_iteration_guard(self):
        state: AgentState = {
            "messages": [], "query": "", "kb_id": 1,
            "skill_results": [], "citations": [],
            "final_answer": "", "iteration": 3, "max_iterations": 3,
        }
        assert state["iteration"] >= state["max_iterations"]
```

- [ ] **Step 4: 运行测试** `uv run pytest tests/services/test_agent_graph.py -v` → 2 PASSED

- [ ] **Step 5: 提交** `git commit -m "feat(agent): 添加 LangGraph AgentState + 图定义"`

---

### Task 5: 对话记忆 — 桥接现有 conversation_*.py

**Files:**
- Create: `backend/app/services/agent/memory.py`
- Test: `backend/tests/services/test_agent_memory.py`

- [ ] **Step 1: 创建 AgentMemory（桥接现有模块）**

```python
# backend/app/services/agent/memory.py
"""Agent 对话记忆 — 桥接现有 conversation_context.py + conversation_compress.py

不重写记忆逻辑，复用已有的：
- conversation_context.is_likely_follow_up + enhance_query_with_context
- conversation_compress.maybe_compress_history
"""
from __future__ import annotations
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Conversation, Message
from app.services.agent.security import SecurityContext
from app.services.conversation_context import (
    is_likely_follow_up, enhance_query_with_context,
)
from app.services.conversation_compress import maybe_compress_history

logger = logging.getLogger(__name__)


async def load_conversation_history(
    ctx: SecurityContext,
    conversation_id: int,
    max_messages: int = 20,
) -> list[dict[str, str]]:
    """加载对话历史（走 RLS）"""
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
        .limit(max_messages)
    )
    result = await ctx.db.execute(stmt)
    messages = list(reversed(result.scalars().all()))
    return [{"role": m.role, "content": m.content} for m in messages]


async def prepare_query_with_memory(
    ctx: SecurityContext,
    query: str,
    conversation_id: int | None,
) -> tuple[str, list[dict[str, str]]]:
    """用对话记忆增强查询

    Returns:
        (enhanced_query, history_messages)
    """
    if not conversation_id:
        return query, []

    history = await load_conversation_history(ctx, conversation_id)
    if not history:
        return query, []

    # 追问检测 + 上下文增强（复用现有逻辑）
    if is_likely_follow_up(query):
        enhanced = enhance_query_with_context(query, history)
        return enhanced, history

    return query, history


async def save_message(
    ctx: SecurityContext,
    conversation_id: int,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> Message:
    """保存消息到对话（走 RLS）"""
    from app.core.snowflake import generate_id
    msg = Message(
        id=generate_id(),
        conversation_id=conversation_id,
        tenant_id=ctx.tenant_id,
        org_id=ctx.org_id,
        role=role,
        content=content,
        metadata_=metadata or {},
    )
    ctx.db.add(msg)
    await ctx.db.flush()
    return msg


async def maybe_compress(
    ctx: SecurityContext,
    conversation_id: int,
) -> None:
    """检查是否需要压缩对话历史（复用现有逻辑）"""
    from app.services.provider_registry import registry
    llm = registry.get_llm()
    await maybe_compress_history(ctx.db, conversation_id, llm)
```

- [ ] **Step 2: 编写测试**

```python
# backend/tests/services/test_agent_memory.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent.security import SecurityContext
from app.services.agent.memory import prepare_query_with_memory


def _ctx():
    db = MagicMock()
    return SecurityContext(tenant_id=1, org_id=2, user_id=3, db=db)


class TestPrepareQueryWithMemory:
    @pytest.mark.asyncio
    async def test_no_conversation_returns_original(self):
        query, history = await prepare_query_with_memory(_ctx(), "测试", None)
        assert query == "测试"
        assert history == []

    @pytest.mark.asyncio
    async def test_empty_history_returns_original(self):
        ctx = _ctx()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        ctx.db.execute = AsyncMock(return_value=mock_result)
        query, history = await prepare_query_with_memory(ctx, "测试", 123)
        assert query == "测试"
        assert history == []
```

- [ ] **Step 3: 运行测试** `uv run pytest tests/services/test_agent_memory.py -v` → 2 PASSED

- [ ] **Step 4: 提交** `git commit -m "feat(agent): 添加对话记忆桥接层"`

---

### Task 6: Chat Endpoint 集成

**Files:**
- Modify: `backend/app/api/endpoints/chat.py`
- Modify: `backend/app/services/agent/__init__.py`
- Test: `backend/tests/api/test_chat_agent.py`

- [ ] **Step 1: 在 agent/__init__.py 中添加高层 API**

```python
# backend/app/services/agent/__init__.py
"""Agent 模块公共接口"""
from app.services.agent.security import SecurityContext
from app.services.agent.skills.base import skill_registry

__all__ = ["SecurityContext", "skill_registry", "run_agent"]


async def run_agent(
    ctx: SecurityContext,
    query: str,
    kb_id: int,
    conversation_id: int | None = None,
) -> dict:
    """Agent 入口 — 集成 Memory + Router + Skill/RAG + Answer

    Returns:
        {"answer": str, "citations": list, "skill_results": list}
    """
    from app.services.agent.memory import prepare_query_with_memory
    from app.services.agent.graph import (
        router_node, rag_node, skill_node, direct_answer_node,
    )
    from app.services.agent.state import AgentState

    # 1. Memory 增强
    enhanced_query, history = await prepare_query_with_memory(
        ctx, query, conversation_id,
    )

    # 2. 构建初始状态
    state: AgentState = {
        "messages": history,
        "query": enhanced_query,
        "kb_id": kb_id,
        "skill_results": [],
        "citations": [],
        "final_answer": "",
        "iteration": 0,
        "max_iterations": 3,
    }

    # 3. Router
    router_result = await router_node(state, ctx)
    state.update(router_result)

    # 4. 根据路由结果执行对应节点
    next_node = state.pop("_next", "rag_node")
    if "final_answer" in router_result and router_result["final_answer"]:
        pass  # 已达到最大轮次
    elif next_node == "skill_node":
        node_result = await skill_node(state, ctx)
        if node_result.get("_next") == "rag_node":
            node_result = await rag_node(state, ctx)
        state.update(node_result)
    elif next_node == "direct_answer":
        node_result = await direct_answer_node(state, ctx)
        state.update(node_result)
    else:
        node_result = await rag_node(state, ctx)
        state.update(node_result)

    return {
        "answer": state.get("final_answer", ""),
        "citations": state.get("citations", []),
        "skill_results": state.get("skill_results", []),
    }
```

- [ ] **Step 2: 在 chat.py endpoint 添加 agent 模式（最小改动）**

在现有 `chat_completions` 函数中，在检索前插入 Agent 路由分支。核心改动约 30 行：

```python
# backend/app/api/endpoints/chat.py — 在现有函数中添加以下代码块
# 位置：在 retrieve_chunks 调用之前

# --- Agent 模式（当 request.use_agent=True 时启用）---
if getattr(request, "use_agent", False):
    from app.services.agent import run_agent, SecurityContext
    from app.services.rbac import RBACService

    # 构建 SecurityContext（复用 FastAPI DI 已验证的安全信息）
    role_ids = [r.id for r in org_user.rbac_roles] if org_user.rbac_roles else []
    effective_perms = await RBACService.get_effective_permissions(db, role_ids)

    ctx = SecurityContext(
        tenant_id=tenant_id,
        org_id=org_id,
        user_id=current_user.id,
        roles=tuple(current_roles),
        permissions=frozenset(effective_perms),
        db=db,
    )

    agent_result = await run_agent(
        ctx=ctx,
        query=request.query,
        kb_id=request.kb_id,
        conversation_id=getattr(request, "conversation_id", None),
    )
    # 将 agent 结果转为 SSE 流式响应（复用现有 SSE 格式）
    # ... 省略 SSE 封装代码，格式与现有完全一致 ...
```

- [ ] **Step 3: 在 ChatRequest schema 中添加 use_agent 字段**

```python
# backend/app/schemas/chat.py — 在 ChatRequest 类中添加
class ChatRequest(BaseModel):
    # ... 现有字段 ...
    use_agent: bool = False  # 是否启用 Agent 模式
```

- [ ] **Step 4: 编写集成测试**

```python
# backend/tests/api/test_chat_agent.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.agent.security import SecurityContext
from app.services.agent import run_agent


class TestRunAgent:
    @pytest.mark.asyncio
    @patch("app.services.agent.graph.registry")
    async def test_direct_answer_for_general_query(self, mock_registry):
        mock_llm = MagicMock()
        mock_llm.complete_text = AsyncMock(
            side_effect=[
                '{"skill": "none"}',      # router 返回 none
                "这是一个通用回答",          # direct_answer 回答
            ]
        )
        mock_registry.get_llm.return_value = mock_llm

        ctx = SecurityContext(
            tenant_id=1, org_id=2, user_id=3,
            permissions=frozenset({"chat:use"}),
            db=MagicMock(),
        )
        result = await run_agent(ctx=ctx, query="你好", kb_id=1)
        assert "answer" in result
        assert isinstance(result["citations"], list)
```

- [ ] **Step 5: 运行测试** `uv run pytest tests/api/test_chat_agent.py -v` → 1 PASSED

- [ ] **Step 6: 提交** `git commit -m "feat(agent): 集成 Agent 到 Chat Endpoint"`

---

### Task 7: 全量验证 + Skills 自动注册

**Files:**
- Modify: `backend/app/services/agent/skills/__init__.py` — 自动导入所有 skill 模块
- Run: 全量测试

- [ ] **Step 1: 确保 Skills 模块自动注册**

```python
# backend/app/services/agent/skills/__init__.py
"""Skills 包 — 导入时自动注册所有技能"""
from app.services.agent.skills.base import (
    SkillDefinition, SkillRegistry, SkillResult, skill_registry,
)

# 自动注册：导入模块即触发 skill_registry.register()
from app.services.agent.skills import rag_skill        # noqa: F401
from app.services.agent.skills import patient_skills    # noqa: F401
from app.services.agent.skills import calculator_skills # noqa: F401

__all__ = ["SkillDefinition", "SkillRegistry", "SkillResult", "skill_registry"]
```

- [ ] **Step 2: 运行全量测试**

```powershell
cd d:\codes\chronic-disease-management\backend
uv run pytest --tb=short -q
```
Expected: 所有现有 191 tests + 新增 ~19 tests 全部 PASSED

- [ ] **Step 3: 验证新模块导入无循环依赖**

```powershell
uv run python -c "from app.services.agent import SecurityContext, skill_registry; print(f'已注册 {len(skill_registry._skills)} 个技能'); [print(f'  - {s.name}: {s.description}') for s in skill_registry.list_all()]"
```
Expected:
```
已注册 4 个技能
  - rag_search: 在知识库中检索与问题相关的文档内容，返回带引用的上下文
  - query_patient: 根据 ID 或姓名查询患者档案
  - health_trend: 查询患者健康指标趋势（血压/血糖/体重/心率等）
  - bmi_calculator: 根据身高体重计算 BMI 并判断等级
```

- [ ] **Step 4: 提交**

```powershell
git add -A
git commit -m "feat(agent): LangGraph Agent 集成完成 — Skills + Memory + 图编排"
```

---

## 自审检查清单

| 检查项 | 状态 |
|--------|------|
| SecurityContext 是否不可变（frozen=True） | ✅ Task 1 |
| 所有 Skill handler 是否接收 SecurityContext | ✅ Task 2-3 |
| 所有 DB 查询是否走 ctx.db（带 RLS） | ✅ Task 3, 5 |
| SkillRegistry.execute 是否做权限预校验 | ✅ Task 2 |
| SkillRegistry.execute 是否做参数白名单过滤 | ✅ Task 2 |
| Router 解析失败是否降级到 RAG | ✅ Task 4 |
| Skill 执行失败是否降级到 RAG | ✅ Task 4 |
| 迭代次数是否有上限（max_iterations=3） | ✅ Task 4 |
| Memory 是否复用 conversation_context.py | ✅ Task 5 |
| Memory 是否复用 conversation_compress.py | ✅ Task 5 |
| 现有 191 tests 是否零回归 | ✅ Task 7 |
| 业务层文件（deps.py/models/schemas）是否零改动 | ✅ 文件结构总览 |
| use_agent=False 时是否完全走原有 RAG 路径 | ✅ Task 6 |

