# 后端三层架构重构设计文档

> **日期**：2026-04-13
> **范围**：后端源代码内部架构重构（API 契约零变更）
> **目标**：将现有的 Router（肥路由）架构重构为 Router → Service → Repository 三层清晰分离

## 1. 背景与问题

### 当前架构

```
Router (routers/)  →  Service (services/)  →  Model (models/)
         ↑                    ↑
    包含大量 DB 查询        层级不完整，~70% 业务逻辑在 Router 中
```

### 核心问题

| 问题 | 表现 |
|------|------|
| **肥路由** | `organizations.py` 402 行，直接写 SQLAlchemy 查询+业务逻辑+事务管理 |
| **缺少 Repository 层** | 所有 DB 操作散落在 Router 和 Service 中，无统一数据访问抽象 |
| **Service 层残缺** | ~12 个路由模块中只有 ~4 个有对应 Service，其余业务逻辑全在 Router |
| **Schema 散乱** | 部分 Pydantic Schema 定义在 Router 文件中（如 `PatientProfileAdminCreate`） |
| **无 DTO 规范** | 后端直接暴露 ORM 模型，缺少统一的分页/响应格式 |

## 2. 设计目标

1. **三层职责分离**：Router（HTTP 适配）→ Service（业务编排）→ Repository（数据访问）
2. **API 契约零变更**：前端无需任何修改，OpenAPI schema 重构前后一致
3. **尊重 FastAPI 生态**：保持 `routers/` 命名，使用 `Annotated` + `Depends` 标准 DI
4. **渐进式迁移**：按业务领域逐模块推进，每阶段可独立验证

## 3. 架构设计

### 3.1 分层职责

```
Router (HTTP 适配层)         routers/     — 参数提取、DI、调 Service、返回 DTO
  ↓
Service (业务编排层)         services/    — 业务逻辑、事务管理、跨 Repo 协调
  ↓
Repository (数据访问层)      repositories/ — SQLAlchemy 查询封装，纯数据操作
  ↓
Model (ORM 模型层)           models/      — 不变
```

### 3.2 各层规范

#### Router 层（瘦路由）

**禁止**：
- 导入 SQLAlchemy（`select`, `func`, `text` 等）
- 调用 `db.execute()` / `db.commit()` / `db.add()`
- 在文件内定义 Pydantic Schema
- 除调用 Service 外的业务判断逻辑

**允许**：
- FastAPI 参数校验（自动完成）
- `Depends()` 依赖注入
- 调用一个 Service 方法
- 返回结果（由 `response_model` 自动序列化）

#### Service 层

**职责**：
- 唯一允许调用 `commit()` 的层
- 不导入任何 FastAPI 类型（APIRouter, Depends, Header 等）
- 通过抛 `BusinessError` 表达业务错误，不返回 HTTP 状态码
- 方法入参和返回值为 Python 原生类型 / ORM 模型
- 可调用其他 Service（通过构造函数组合）

#### Repository 层

**职责**：
- 封装所有 SQLAlchemy 查询
- 只使用 `flush()` 而非 `commit()`（事务控制权在 Service）
- 纯数据访问，无业务决策
- 通过 `BaseRepository[T]` 泛型基类提供标准 CRUD

### 3.3 BaseRepository 设计

```python
# repositories/base.py
from typing import Generic, TypeVar
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")

class BaseRepository(Generic[ModelType]):
    def __init__(self, db: AsyncSession, model: type[ModelType]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: int) -> ModelType | None:
        return await self.db.get(self.model, id)

    async def list(self, *, skip: int = 0, limit: int = 50,
                   filters: list = None, order_by=None) -> list[ModelType]:
        stmt = select(self.model)
        for f in (filters or []):
            stmt = stmt.where(f)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, filters: list = None) -> int:
        stmt = select(func.count()).select_from(self.model)
        for f in (filters or []):
            stmt = stmt.where(f)
        return (await self.db.execute(stmt)).scalar() or 0

    async def create(self, obj: ModelType) -> ModelType:
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType, data: dict) -> ModelType:
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        await self.db.delete(obj)
        await self.db.flush()
```

### 3.4 依赖注入策略

使用 FastAPI 官方推荐的 `Annotated` + 泛型工厂模式：

```python
# routers/deps.py
from typing import Annotated, TypeVar

S = TypeVar("S")

def ServiceDep(service_cls: type[S]):
    """通用 Service 依赖工厂"""
    async def _factory(db: AsyncSession = Depends(get_db)):
        return service_cls(db)
    return Depends(_factory)

# 类型别名 — 每个 Service 一行
PatientServiceDep      = Annotated[PatientService, ServiceDep(PatientService)]
HealthMetricServiceDep = Annotated[HealthMetricService, ServiceDep(HealthMetricService)]
OrgServiceDep          = Annotated[OrgService, ServiceDep(OrgService)]
# ...
```

Router 使用：

```python
@router.get("", response_model=list[PatientProfileRead])
async def list_patients(
    service: PatientServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    ...
):
    return await service.list_patients(tenant_id, ...)
```

### 3.5 异常策略

Service 层抛业务异常，main.py 统一转 HTTP 响应：

```python
# base/exceptions.py — 扩展
class BusinessError(Exception):
    def __init__(self, message: str, code: str = "BUSINESS_ERROR"):
        self.message = message
        self.code = code

class NotFoundError(BusinessError):
    def __init__(self, resource: str, id: int | str | None = None):
        msg = f"{resource} not found" + (f" (id={id})" if id else "")
        super().__init__(msg, code="NOT_FOUND")

class ConflictError(BusinessError):
    def __init__(self, message: str):
        super().__init__(message, code="CONFLICT")

class PermissionDeniedError(BusinessError):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(message, code="PERMISSION_DENIED")

class QuotaExceededError(BusinessError):
    def __init__(self, message: str = "Quota exceeded"):
        super().__init__(message, code="QUOTA_EXCEEDED")
```

```python
# main.py 注册异常处理器
@app.exception_handler(BusinessError)
async def business_error_handler(request, exc: BusinessError):
    status_map = {
        "NOT_FOUND": 404,
        "CONFLICT": 409,
        "PERMISSION_DENIED": 403,
        "QUOTA_EXCEEDED": 402,
        "BUSINESS_ERROR": 400,
    }
    return ORJSONResponse(
        status_code=status_map.get(exc.code, 400),
        content={"detail": exc.message, "code": exc.code},
    )
```

### 3.6 Schema/DTO 整理

所有 Pydantic Schema 统一到 `schemas/` 目录，按领域组织：

```
schemas/
├── common.py           # PagedResponse[T], StatusResponse 等通用 DTO
├── patient.py          # 补充 PatientProfileAdminCreate 等散落的 Schema
├── health_metric.py    # 新增
├── manager.py          # 新增
├── family.py           # 新增
├── organization.py     # 补充 AddMemberRequest 等
├── user.py             # 已存在
├── rbac.py             # 已存在
├── menu.py             # 已存在
├── tenant.py           # 新增
├── knowledge_base.py   # 新增
├── conversation.py     # 新增
├── dashboard.py        # 新增
├── audit.py            # 新增
├── auth.py             # 新增
├── api_key.py          # 已存在
└── document.py         # 已存在
```

通用分页 DTO：

```python
# schemas/common.py
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PagedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    skip: int
    limit: int

class StatusResponse(BaseModel):
    status: str = "ok"
    message: str | None = None
```

## 4. 文件清单

### 4.1 新增文件

**repositories/**（~17 个文件）：

| 文件 | 职责 |
|------|------|
| `base.py` | BaseRepository[T] 泛型基类 |
| `patient_repo.py` | PatientProfile 数据访问 |
| `health_metric_repo.py` | HealthMetric 数据访问 |
| `manager_repo.py` | ManagerProfile + Assignment + Suggestion |
| `family_repo.py` | PatientFamilyLink |
| `org_repo.py` | Organization + OrganizationInvitation |
| `org_user_repo.py` | OrganizationUser + OrganizationUserRole |
| `user_repo.py` | User |
| `tenant_repo.py` | Tenant |
| `role_repo.py` | Role + Permission + RoleConstraint |
| `menu_repo.py` | Menu |
| `kb_repo.py` | KnowledgeBase + Document + Chunk |
| `conversation_repo.py` | Conversation + Message |
| `usage_repo.py` | UsageLog |
| `audit_repo.py` | AuditLog |
| `api_key_repo.py` | ApiKey |
| `settings_repo.py` | SystemSetting |

**services/**（~12 个新增文件）：

| 文件 | 职责 |
|------|------|
| `patient/patient_service.py` | 患者档案 CRUD |
| `patient/health_metric_service.py` | 健康指标 CRUD + 告警触发 |
| `patient/manager_service.py` | 管理师 + 分配 + 建议 |
| `patient/family_service.py` | 家属关联 |
| `system/org_service.py` | 组织 + 成员 + 邀请 |
| `system/user_service.py` | 用户管理 |
| `system/tenant_service.py` | 租户管理 |
| `system/dashboard_service.py` | 统计查询 |
| `system/menu_service.py` | 菜单管理 |
| `rag/kb_service.py` | 知识库 CRUD |
| `rag/conversation_service.py` | 对话管理 |
| `auth/auth_service.py` | 登录/注册/切换组织 |

**schemas/**（~7 个新增文件）：

| 文件 | 内容 |
|------|------|
| `common.py` | PagedResponse, StatusResponse |
| `health_metric.py` | 健康指标 DTO |
| `manager.py` | 管理师 DTO |
| `family.py` | 家属关联 DTO |
| `tenant.py` | 租户 DTO |
| `knowledge_base.py` | 知识库 DTO |
| `conversation.py` | 对话 DTO |
| `dashboard.py` | 仪表盘 DTO |
| `audit.py` | 审计日志 DTO |
| `auth.py` | 认证 DTO |

### 4.2 修改文件

| 文件 | 改动 |
|------|------|
| `base/exceptions.py` | 新增 BusinessError 异常体系 |
| `main.py` | 新增 BusinessError 异常处理器 |
| `routers/deps.py` | 新增 ServiceDep 泛型工厂 + 类型别名 |
| `routers/patient/*.py` (4 个) | 瘦身：移除 DB 查询，调用 Service |
| `routers/system/*.py` (~10 个) | 瘦身：移除 DB 查询，调用 Service |
| `routers/rag/*.py` (4 个) | 瘦身：移除 DB 查询，调用 Service |
| `routers/auth/router.py` | 瘦身 |
| `schemas/patient.py` | 补充从 Router 移来的 Schema |
| `schemas/organization.py` | 补充从 Router 移来的 Schema |
| `services/rag/chat_service.py` | 内部 DB 查询下沉到 conversation_repo |

### 4.3 不变的模块

- `models/` — ORM 模型层
- `base/`（除 exceptions.py 外）— 基础设施层
- `ai/` — AI 领域层
- `plugins/` — 插件体系
- `tasks/` — arq 异步任务
- `telemetry/` — 可观测性
- `seed.py` — 种子数据

## 5. 迁移策略

### Phase 0：基础设施搭建

- 创建 `base/exceptions.py` 扩展（BusinessError 体系）
- 创建 `repositories/base.py`（BaseRepository）
- `deps.py` 添加 ServiceDep 泛型工厂
- `main.py` 注册 BusinessError handler

### Phase 1：Patient 领域（模板模块）

- `repositories/patient_repo.py` + `services/patient/patient_service.py`
- 瘦身 `routers/patient/patients.py`
- 整理 `schemas/patient.py`
- 同样处理 health_metrics、managers、family
- 验证：所有 `/patients/*`、`/health-metrics/*`、`/managers/*`、`/family/*` 端点行为不变

### Phase 2：System 领域

- organizations（最复杂，402 行 → ~80 行）
- users、tenants、rbac、dashboard、menus
- api_keys、settings、usage
- 验证：所有 system 端点行为不变

### Phase 3：RAG 领域

- knowledge_bases、conversations
- chat_service / document_service 内部 DB 查询下沉到 repo
- 验证：所有 RAG 端点行为不变

### Phase 4：Auth + Audit

- auth_service 抽取
- 审计模块微调

### Phase 5：收尾验证

- 全量测试通过
- OpenAPI schema diff = 0
- 更新 AGENTS.md 架构文档

## 6. 验证标准

每完成一个模块：

1. **功能不变**：所有端点返回结果与重构前一致
2. **Router 干净**：没有 `sqlalchemy` 导入、没有 `db.execute` / `db.commit`
3. **测试通过**：现有测试 + 新增 Service/Repository 测试
4. **类型正确**：IDE 无类型错误

最终验证：

5. **OpenAPI schema diff = 0**
6. **AGENTS.md 更新完成**
