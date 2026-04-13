# 后端三层架构重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将后端从肥路由架构重构为 Router → Service → Repository 三层分离，API 契约零变更

**Architecture:** 新增 Repository 数据访问层（BaseRepository 泛型基类），补全 Service 业务编排层（~12 个新 Service），瘦身所有 Router（移除直写的 SQLAlchemy 查询），统一业务异常体系（BusinessError），整理散落的 Schema/DTO

**Tech Stack:** FastAPI, SQLAlchemy 2.x Async, Pydantic v2, Annotated + Depends DI

---

## Phase 0: 基础设施搭建

### Task 1: BusinessError 异常体系

**Files:**
- Modify: `app/base/exceptions.py`
- Modify: `app/main.py`

- [ ] **Step 1: 重写 exceptions.py，建立不依赖 HTTPException 的业务异常体系**

```python
"""统一业务异常定义

Service 层抛出这些异常，main.py 的 exception_handler 统一转换为 HTTP 响应。
这样 Service 层不需要依赖 FastAPI 的 HTTPException。
"""


class BusinessError(Exception):
    """业务异常基类"""

    def __init__(self, message: str, code: str = "BUSINESS_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class NotFoundError(BusinessError):
    def __init__(self, resource: str = "Resource", id: int | str | None = None):
        msg = f"{resource} not found" + (f" (id={id})" if id else "")
        super().__init__(msg, code="NOT_FOUND")


class ForbiddenError(BusinessError):
    def __init__(self, message: str = "Not enough permissions"):
        super().__init__(message, code="FORBIDDEN")


class ConflictError(BusinessError):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message, code="CONFLICT")


class QuotaExceededError(BusinessError):
    def __init__(self, message: str = "Quota exceeded"):
        super().__init__(message, code="QUOTA_EXCEEDED")


class ValidationError(BusinessError):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message, code="VALIDATION_ERROR")
```

- [ ] **Step 2: 在 main.py 注册 BusinessError 异常处理器**

在 `app/main.py` 中，在现有 `@app.exception_handler(HTTPException)` 之前插入：

```python
from app.base.exceptions import BusinessError

@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    status_map = {
        "NOT_FOUND": 404,
        "CONFLICT": 409,
        "FORBIDDEN": 403,
        "QUOTA_EXCEEDED": 402,
        "VALIDATION_ERROR": 422,
        "BUSINESS_ERROR": 400,
    }
    return SnowflakeJSONResponse(
        status_code=status_map.get(exc.code, 400),
        content={"detail": exc.message, "code": exc.code},
    )
```

- [ ] **Step 3: 验证应用启动正常**

```bash
cd backend; uv run python -c "from app.main import app; print('OK')"
```

- [ ] **Step 4: 提交**

```bash
git add app/base/exceptions.py app/main.py
git commit -m "refactor: 重建 BusinessError 异常体系，脱离 HTTPException 依赖"
```

---

### Task 2: BaseRepository 泛型基类

**Files:**
- Create: `app/repositories/__init__.py`
- Create: `app/repositories/base.py`

- [ ] **Step 1: 创建 repositories 目录和 __init__.py**

```python
# app/repositories/__init__.py
"""Repository 层 — 数据访问抽象"""
```

- [ ] **Step 2: 创建 BaseRepository**

```python
# app/repositories/base.py
"""通用数据访问基类，提供标准 CRUD 操作

Repository 只使用 flush() 而非 commit()，事务控制权在 Service 层。
"""

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """泛型 Repository 基类"""

    def __init__(self, db: AsyncSession, model: type[ModelType]):
        self.db = db
        self.model = model

    async def get_by_id(self, id: int) -> ModelType | None:
        """按主键获取"""
        return await self.db.get(self.model, id)

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        filters: list[Any] | None = None,
        order_by: Any = None,
    ) -> list[ModelType]:
        """通用列表查询"""
        stmt = select(self.model)
        for f in filters or []:
            stmt = stmt.where(f)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, *, filters: list[Any] | None = None) -> int:
        """通用计数"""
        stmt = select(func.count()).select_from(self.model)
        for f in filters or []:
            stmt = stmt.where(f)
        return (await self.db.execute(stmt)).scalar() or 0

    async def create(self, obj: ModelType) -> ModelType:
        """插入对象（flush，不 commit）"""
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def update(self, obj: ModelType, data: dict[str, Any]) -> ModelType:
        """部分更新（flush，不 commit）"""
        for key, value in data.items():
            setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj

    async def delete(self, obj: ModelType) -> None:
        """删除对象（flush，不 commit）"""
        await self.db.delete(obj)
        await self.db.flush()
```

- [ ] **Step 3: 提交**

```bash
git add app/repositories/
git commit -m "refactor: 新增 BaseRepository 泛型基类"
```

---

### Task 3: deps.py 添加 ServiceDep 泛型工厂

**Files:**
- Modify: `app/routers/deps.py`

- [ ] **Step 1: 在 deps.py 顶部添加工厂和导出标记**

在 `app/routers/deps.py` 文件末尾追加 ServiceDep 工厂和 schemas 通用 DTO：

```python
# ── Service 依赖注入工厂 ──

from typing import Annotated, TypeVar

S = TypeVar("S")


def ServiceDep(service_cls: type[S]):
    """通用 Service 依赖工厂

    用法：
        PatientServiceDep = Annotated[PatientService, ServiceDep(PatientService)]
    """

    async def _factory(db: AsyncSession = Depends(get_db)) -> S:
        return service_cls(db)

    return Depends(_factory)
```

> **注意**：具体的 `XxxServiceDep` 类型别名将在每个 Phase 中按需添加，避免一次性引入大量未实现的 Service 导入。

- [ ] **Step 2: 提交**

```bash
git add app/routers/deps.py
git commit -m "refactor: deps.py 添加 ServiceDep 泛型工厂"
```

---

### Task 4: 通用 Schema/DTO

**Files:**
- Create: `app/schemas/common.py`

- [ ] **Step 1: 创建通用 DTO**

```python
# app/schemas/common.py
"""通用响应 DTO"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PagedResponse(BaseModel, Generic[T]):
    """统一分页响应格式"""

    items: list[T]
    total: int
    skip: int
    limit: int


class StatusResponse(BaseModel):
    """统一状态响应"""

    status: str = "ok"
    message: str | None = None
```

- [ ] **Step 2: 提交**

```bash
git add app/schemas/common.py
git commit -m "refactor: 新增通用 PagedResponse / StatusResponse DTO"
```

---

## Phase 1: Patient 领域

### Task 5: PatientRepository + PatientService + 瘦身 patients.py

**Files:**
- Create: `app/repositories/patient_repo.py`
- Create: `app/services/patient/patient_service.py`
- Modify: `app/schemas/patient.py` (补充散落的 Schema)
- Modify: `app/routers/deps.py` (添加 PatientServiceDep)
- Modify: `app/routers/patient/patients.py` (瘦身)

- [ ] **Step 1: 创建 PatientRepository**

```python
# app/repositories/patient_repo.py
"""患者档案数据访问"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ManagementSuggestion, PatientProfile
from app.repositories.base import BaseRepository


class PatientRepository(BaseRepository[PatientProfile]):
    def __init__(self, db: AsyncSession):
        super().__init__(db, PatientProfile)

    async def find_by_user_and_org(
        self, user_id: int, org_id: int
    ) -> PatientProfile | None:
        """按用户 ID + 组织 ID 查找患者档案"""
        stmt = select(PatientProfile).where(
            PatientProfile.user_id == user_id,
            PatientProfile.org_id == org_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        tenant_id: int,
        org_id: int | None = None,
        name: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PatientProfile]:
        """带搜索、分页、部门过滤的患者查询"""
        filters = [PatientProfile.tenant_id == tenant_id]
        if org_id is not None:
            filters.append(PatientProfile.org_id == org_id)
        if name:
            filters.append(PatientProfile.real_name.ilike(f"%{name}%"))
        return await self.list(
            filters=filters,
            skip=skip,
            limit=limit,
            order_by=PatientProfile.created_at.desc(),
        )

    async def get_suggestions_for_patient(
        self, patient_id: int, org_id: int
    ) -> list[ManagementSuggestion]:
        """获取患者的管理建议"""
        stmt = (
            select(ManagementSuggestion)
            .where(
                ManagementSuggestion.patient_id == patient_id,
                ManagementSuggestion.org_id == org_id,
            )
            .order_by(ManagementSuggestion.created_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
```

- [ ] **Step 2: 补充 schemas/patient.py（将散落的 Schema 移入）**

在 `app/schemas/patient.py` 末尾追加从 `patients.py` router 中移来的 Schema：

```python
class PatientProfileAdminCreate(BaseModel):
    """管理员创建患者档案"""

    user_id: int
    real_name: str
    gender: str | None = None
    birth_date: str | None = None
    medical_history: dict | None = None
```

- [ ] **Step 3: 创建 PatientService**

```python
# app/services/patient/patient_service.py
"""患者档案业务服务"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.base.exceptions import ConflictError, NotFoundError
from app.models import PatientProfile, User
from app.repositories.patient_repo import PatientRepository


class PatientService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PatientRepository(db)

    async def list_patients(
        self,
        *,
        tenant_id: int,
        org_id: int | None = None,
        search: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[PatientProfile]:
        return await self.repo.search(
            tenant_id=tenant_id, org_id=org_id, name=search, skip=skip, limit=limit
        )

    async def get_my_profile(
        self, user_id: int, org_id: int
    ) -> PatientProfile:
        profile = await self.repo.find_by_user_and_org(user_id, org_id)
        if not profile:
            raise NotFoundError("Patient profile")
        return profile

    async def get_patient(
        self,
        patient_id: int,
        tenant_id: int,
        org_id: int | None = None,
    ) -> PatientProfile:
        patient = await self.repo.get_by_id(patient_id)
        if not patient or patient.tenant_id != tenant_id:
            raise NotFoundError("Patient", patient_id)
        if org_id is not None and patient.org_id != org_id:
            raise NotFoundError("Patient", patient_id)
        return patient

    async def update_my_profile(
        self,
        user_id: int,
        tenant_id: int,
        org_id: int,
        data: dict,
    ) -> PatientProfile:
        profile = await self.repo.find_by_user_and_org(user_id, org_id)
        if not profile:
            profile = PatientProfile(
                user_id=user_id,
                tenant_id=tenant_id,
                org_id=org_id,
                real_name="Unnamed",
            )
            await self.repo.create(profile)
        if data:
            await self.repo.update(profile, data)
        await self.db.commit()
        return profile

    async def admin_update_patient(
        self,
        patient_id: int,
        tenant_id: int,
        org_id: int | None,
        data: dict,
    ) -> PatientProfile:
        patient = await self.get_patient(patient_id, tenant_id, org_id)
        await self.repo.update(patient, data)
        await self.db.commit()
        return patient

    async def admin_create_patient(
        self,
        *,
        user_id: int,
        tenant_id: int,
        org_id: int,
        real_name: str,
        gender: str | None = None,
        medical_history: dict | None = None,
    ) -> PatientProfile:
        # 验证用户存在
        user = await self.db.get(User, user_id)
        if not user:
            raise NotFoundError("User", user_id)

        # 检查重复
        existing = await self.repo.find_by_user_and_org(user_id, org_id)
        if existing:
            raise ConflictError("Patient profile already exists")

        profile = PatientProfile(
            user_id=user_id,
            tenant_id=tenant_id,
            org_id=org_id,
            real_name=real_name,
            gender=gender,
            medical_history=medical_history,
        )
        await self.repo.create(profile)
        await self.db.commit()
        return profile

    async def delete_patient(
        self,
        patient_id: int,
        tenant_id: int,
        org_id: int | None = None,
    ) -> None:
        patient = await self.get_patient(patient_id, tenant_id, org_id)
        await self.repo.delete(patient)
        await self.db.commit()

    async def get_my_suggestions(
        self, user_id: int, org_id: int
    ) -> list:
        profile = await self.get_my_profile(user_id, org_id)
        return await self.repo.get_suggestions_for_patient(profile.id, org_id)
```

- [ ] **Step 4: 在 deps.py 添加 PatientServiceDep**

在 `app/routers/deps.py` 末尾 ServiceDep 工厂之后追加：

```python
from app.services.patient.patient_service import PatientService

PatientServiceDep = Annotated[PatientService, ServiceDep(PatientService)]
```

- [ ] **Step 5: 瘦身 routers/patient/patients.py**

将整个文件替换为：

```python
"""患者档案路由 — 纯 HTTP 适配层"""

from typing import Any

from fastapi import APIRouter, Depends

from app.models import User
from app.routers.deps import (
    PatientServiceDep,
    check_permission,
    get_current_org_id,
    get_current_tenant_id,
    get_current_user,
    get_effective_org_id,
    inject_rls_context,
)
from app.schemas.patient import (
    PatientProfileAdminCreate,
    PatientProfileRead,
    PatientProfileUpdate,
)

router = APIRouter()


@router.get("", response_model=list[PatientProfileRead])
async def list_patients(
    service: PatientServiceDep,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:read")),
):
    """[管理视图] 列出患者"""
    return await service.list_patients(
        tenant_id=tenant_id, org_id=effective_org_id, search=search, skip=skip, limit=limit
    )


@router.get("/me", response_model=PatientProfileRead)
async def get_my_patient_profile(
    service: PatientServiceDep,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org_id),
) -> Any:
    """[个人视图] 获取当前用户自己的患者档案"""
    return await service.get_my_profile(current_user.id, org_id)


@router.get("/{patient_id}", response_model=PatientProfileRead)
async def get_patient_detail(
    patient_id: int,
    service: PatientServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:read")),
):
    """[管理视图] 获取特定患者详情"""
    return await service.get_patient(patient_id, tenant_id, effective_org_id)


@router.put("/me", response_model=PatientProfileRead)
async def update_my_patient_profile(
    profile_in: PatientProfileUpdate,
    service: PatientServiceDep,
    current_user: User = Depends(get_current_user),
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
) -> Any:
    """[个人视图] 更新当前用户自己的患者档案"""
    return await service.update_my_profile(
        current_user.id, tenant_id, org_id, profile_in.model_dump(exclude_unset=True)
    )


@router.put("/{patient_id}", response_model=PatientProfileRead)
async def admin_update_patient(
    patient_id: int,
    profile_in: PatientProfileUpdate,
    service: PatientServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:update")),
):
    """[管理视图] 管理员修改患者信息"""
    return await service.admin_update_patient(
        patient_id, tenant_id, effective_org_id, profile_in.model_dump(exclude_unset=True)
    )


@router.get("/me/suggestions")
async def get_my_suggestions(
    service: PatientServiceDep,
    current_user: User = Depends(get_current_user),
    org_id: int = Depends(get_current_org_id),
):
    """[患者视图] 查看管理师给自己的管理建议"""
    return await service.get_my_suggestions(current_user.id, org_id)


@router.post("/create")
async def admin_create_patient_profile(
    data: PatientProfileAdminCreate,
    service: PatientServiceDep,
    tenant_id: int = Depends(get_current_tenant_id),
    org_id: int = Depends(get_current_org_id),
    _permission=Depends(check_permission("patient:create")),
) -> Any:
    """[管理视图] 为用户创建患者档案"""
    profile = await service.admin_create_patient(
        user_id=data.user_id,
        tenant_id=tenant_id,
        org_id=org_id,
        real_name=data.real_name,
        gender=data.gender,
        medical_history=data.medical_history,
    )
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "org_id": profile.org_id,
        "real_name": profile.real_name,
        "gender": profile.gender,
    }


@router.delete("/{patient_id}")
async def delete_patient_profile(
    patient_id: int,
    service: PatientServiceDep,
    tenant_id: int = Depends(inject_rls_context),
    effective_org_id: int | None = Depends(get_effective_org_id),
    _permission=Depends(check_permission("patient:delete")),
) -> Any:
    """[管理视图] 删除患者档案"""
    await service.delete_patient(patient_id, tenant_id, effective_org_id)
    return {"status": "ok"}
```

- [ ] **Step 6: 验证应用启动、端点可用**

```bash
cd backend; uv run python -c "from app.main import app; print('OK')"
```

- [ ] **Step 7: 运行现有测试**

```bash
cd backend; uv run pytest tests/ -x -q
```

- [ ] **Step 8: 提交**

```bash
git add app/repositories/patient_repo.py app/services/patient/patient_service.py app/schemas/patient.py app/routers/deps.py app/routers/patient/patients.py
git commit -m "refactor(patient): 拆分三层架构 — PatientRepository + PatientService + 瘦身 Router"
```

---

### Task 6: HealthMetricRepository + HealthMetricService + 瘦身 health_metrics.py

**Files:**
- Create: `app/repositories/health_metric_repo.py`
- Create: `app/services/patient/health_metric_service.py`
- Create: `app/schemas/health_metric.py` (从 router 中迁出 Schema)
- Modify: `app/routers/deps.py` (添加 HealthMetricServiceDep)
- Modify: `app/routers/patient/health_metrics.py` (瘦身)

> 由于篇幅限制，后续 Task 的代码结构与 Task 5 相同，按照「创建 Repo → 迁移 Schema → 创建 Service → 注册 Dep → 瘦身 Router → 验证 → 提交」的标准流程执行。

- [ ] **Step 1: 创建 health_metric_repo.py**

封装以下查询：`find_by_patient_and_type`、`get_trend`（按时间范围查询趋势数据）、`find_owned_metric`（按 ID 查找并验证所有权）。

- [ ] **Step 2: 创建 schemas/health_metric.py**

将 `HealthMetricCreate`、`HealthMetricRead`、`HealthMetricUpdate` 从 `health_metrics.py` router 迁移过来。包含 `ALLOWED_METRIC_TYPES` 常量。

- [ ] **Step 3: 创建 health_metric_service.py**

方法：`create_metric`（含告警检测调用）、`list_my_metrics`、`get_my_trend`、`update_metric`（验证所有权）、`delete_metric`（验证所有权）、`get_patient_trend`（管理端视图，验证 tenant/org）。

- [ ] **Step 4: deps.py 添加 HealthMetricServiceDep**
- [ ] **Step 5: 瘦身 health_metrics.py router** — 移除所有 SQLAlchemy 导入和查询
- [ ] **Step 6: 验证 + 提交**

```bash
git commit -m "refactor(health-metric): 拆分三层架构"
```

---

### Task 7: ManagerRepository + ManagerService + 瘦身 managers.py

**Files:**
- Create: `app/repositories/manager_repo.py`
- Create: `app/services/patient/manager_service.py`
- Create: `app/schemas/manager.py` (从 router 迁出)
- Modify: `app/routers/deps.py`
- Modify: `app/routers/patient/managers.py`

- [ ] **Step 1: 创建 manager_repo.py**

封装：`list_with_user`（含 selectinload user）、`count_assignments`、`find_by_user_and_org`、`upsert_assignment`（PostgreSQL ON CONFLICT）、`delete_assignments`、`find_suggestion`、`list_suggestions`。

- [ ] **Step 2: 创建 schemas/manager.py**

迁移：`ManagerDetailRead`、`PatientBriefRead`、`SuggestionCreate`、`SuggestionRead`、`AssignmentCreate`、`ManagerProfileCreate`、`ManagerProfileUpdate`、`SuggestionUpdate`。

- [ ] **Step 3: 创建 manager_service.py**

方法对应 12 个路由端点。

- [ ] **Step 4-6: 注册 Dep → 瘦身 Router → 验证提交**

```bash
git commit -m "refactor(manager): 拆分三层架构"
```

---

### Task 8: FamilyService + 瘦身 family.py

**Files:**
- Create: `app/repositories/family_repo.py`
- Create: `app/services/patient/family_service.py`
- Create: `app/schemas/family.py` (从 router 迁出)
- Modify: `app/routers/deps.py`
- Modify: `app/routers/patient/family.py`

- [ ] **Step 1: 创建 family_repo.py** — 封装家属链接 CRUD 查询
- [ ] **Step 2: 迁移 schemas** — `FamilyLinkCreate`、`FamilyLinkRead`、`PatientProfileFamilyRead`
- [ ] **Step 3: 创建 family_service.py** — 方法：`create_link`、`get_my_patients`、`get_patient_profile`（含审计）、`unlink`
- [ ] **Step 4-6: 注册 Dep → 瘦身 Router → 验证提交**

```bash
git commit -m "refactor(family): 拆分三层架构"
```

---

## Phase 2: System 领域

### Task 9: OrgRepository + OrgService + 瘦身 organizations.py

**Files:**
- Create: `app/repositories/org_repo.py`
- Create: `app/services/system/org_service.py`
- Modify: `app/schemas/organization.py` (补充 AddMemberRequest)
- Modify: `app/routers/deps.py`
- Modify: `app/routers/system/organizations.py` (402行 → ~90行)

- [ ] **Step 1: 创建 org_repo.py**

封装：`find_by_code_and_tenant`、`list_by_tenant`（含 count）、`count_members`、`list_members`（含 user + roles selectinload）、`find_org_user`、`find_invitation_by_token`。

- [ ] **Step 2: 补充 schemas/organization.py** — 移入 `AddMemberRequest`
- [ ] **Step 3: 创建 org_service.py** — 10 个方法对应 10 个端点
- [ ] **Step 4-6: 注册 Dep → 瘦身 Router → 验证提交**

```bash
git commit -m "refactor(organization): 拆分三层架构，402行→~90行"
```

---

### Task 10: UserService + 瘦身 users.py

**Files:**
- Create: `app/repositories/user_repo.py`
- Create: `app/services/system/user_service.py`
- Modify: `app/schemas/user.py` (补充 UserCreateAdmin, UserUpdate)
- Modify: `app/routers/deps.py`
- Modify: `app/routers/system/users.py`

- [ ] **Step 1-6: Repo → Schema → Service → Dep → Router → 提交**

```bash
git commit -m "refactor(user): 拆分三层架构"
```

---

### Task 11: TenantService + 瘦身 tenants.py

**Files:**
- Create: `app/repositories/tenant_repo.py`
- Create: `app/services/system/tenant_service.py`
- Create: `app/schemas/tenant.py` (从 router 迁出)
- Modify: `app/routers/deps.py`
- Modify: `app/routers/system/tenants.py`

- [ ] **Step 1-6: Repo → Schema → Service → Dep → Router → 提交**

```bash
git commit -m "refactor(tenant): 拆分三层架构"
```

---

### Task 12: DashboardService + 瘦身 dashboard.py

**Files:**
- Create: `app/services/system/dashboard_service.py`
- Modify: `app/routers/deps.py`
- Modify: `app/routers/system/dashboard.py`

> Dashboard 的查询较为特殊（大量聚合统计），Repository 层可以用一个 `DashboardRepository` 封装统计查询，也可以让 Service 直接持有 db 做复杂聚合。推荐后者，因为这些是只读聚合查询，不涉及 CRUD 实体操作。

- [ ] **Step 1: 创建 dashboard_service.py** — `get_tenant_stats`、`get_platform_stats`
- [ ] **Step 2-4: Dep → Router → 提交**

```bash
git commit -m "refactor(dashboard): 拆分三层架构"
```

---

### Task 13: MenuService + 瘦身 menus.py

**Files:**
- Create: `app/repositories/menu_repo.py`
- Create: `app/services/system/menu_service.py`
- Create: `app/schemas/menu.py` (从 router 迁出)
- Modify: `app/routers/deps.py`
- Modify: `app/routers/system/menus.py`

- [ ] **Step 1-6: Repo → Schema → Service → Dep → Router → 提交**

```bash
git commit -m "refactor(menu): 拆分三层架构"
```

---

### Task 14: RbacService 扩展 + 瘦身 rbac.py router

**Files:**
- Create: `app/repositories/role_repo.py`
- Modify: `app/services/system/rbac.py` (扩展 CRUD)
- Create: `app/schemas/rbac_ext.py` (补充 RoleUpdate)
- Modify: `app/routers/deps.py`
- Modify: `app/routers/system/rbac.py`

- [ ] **Step 1-6: Repo → Schema → Service 扩展 → Dep → Router → 提交**

```bash
git commit -m "refactor(rbac): 拆分三层架构"
```

---

### Task 15: 剩余 System 路由瘦身 (api_keys, settings, usage, external_api)

**Files:**
- Modify: `app/routers/system/api_keys.py`
- Modify: `app/routers/system/settings.py`
- Modify: `app/routers/system/usage.py`
- Modify: `app/routers/system/external_api.py`
- 按需创建对应的 Repository + Service

- [ ] **Step 1-4: 逐个瘦身 → 验证 → 提交**

```bash
git commit -m "refactor(system): 剩余路由三层架构瘦身"
```

---

## Phase 3: RAG 领域

### Task 16: KBRepository + KBService + 瘦身 knowledge_bases.py

**Files:**
- Create: `app/repositories/kb_repo.py`
- Create: `app/services/rag/kb_service.py`
- Create: `app/schemas/knowledge_base.py` (从 router 迁出)
- Modify: `app/routers/deps.py`
- Modify: `app/routers/rag/knowledge_bases.py`

- [ ] **Step 1-6: 标准流程**

```bash
git commit -m "refactor(kb): 拆分三层架构"
```

---

### Task 17: ConversationRepository + ConversationService + 瘦身 conversations.py

**Files:**
- Create: `app/repositories/conversation_repo.py`
- Create: `app/services/rag/conversation_service.py`
- Create: `app/schemas/conversation.py` (从 router 迁出)
- Modify: `app/routers/deps.py`
- Modify: `app/routers/rag/conversations.py`

- [ ] **Step 1-6: 标准流程**

```bash
git commit -m "refactor(conversation): 拆分三层架构"
```

---

### Task 18: chat_service.py 内部 DB 查询下沉

**Files:**
- Modify: `app/services/rag/chat_service.py`
- 使用: `app/repositories/conversation_repo.py` (Task 17 创建)

- [ ] **Step 1: 将 chat_service.py 中的 `_get_or_create_conversation` 和 `_load_history` 改为调用 ConversationRepository**
- [ ] **Step 2: 验证 + 提交**

```bash
git commit -m "refactor(chat): DB 查询下沉到 ConversationRepository"
```

---

## Phase 4: Auth 领域

### Task 19: AuthService + 瘦身 auth/router.py

**Files:**
- Create: `app/repositories/auth_repo.py`
- Create: `app/services/auth/auth_service.py`
- Create: `app/schemas/auth.py` (从 router 迁出)
- Modify: `app/routers/deps.py`
- Modify: `app/routers/auth/router.py` (574行 → ~120行)

> Auth router 是第二胖的文件（574 行），包含注册、登录（多部门选择）、切换组织、菜单树、密码重置等复杂逻辑。

- [ ] **Step 1: 创建 auth_repo.py** — 封装用户查找、组织成员查找、密码重置 token 查找
- [ ] **Step 2: 创建 schemas/auth.py** — 迁出 `SelectOrgRequest`、`SwitchOrgRequest`、`ForgotPasswordRequest`、`ResetPasswordRequest`、`UserProfileUpdate`
- [ ] **Step 3: 创建 auth_service.py** — 方法：`register`、`login`、`select_org`、`switch_org`、`list_my_orgs`、`get_me`、`get_menu_tree`、`update_password`、`update_profile`、`forgot_password`、`reset_password`
- [ ] **Step 4-6: Dep → Router → 提交**

```bash
git commit -m "refactor(auth): 拆分三层架构，574行→~120行"
```

---

## Phase 5: 收尾验证

### Task 20: 全量验证 + 文档更新

**Files:**
- Test: all tests
- Modify: `AGENTS.md` (更新架构文档)

- [ ] **Step 1: 全量测试**

```bash
cd backend; uv run pytest tests/ -v
```

- [ ] **Step 2: 验证 Router 无 SQLAlchemy 导入**

```bash
cd backend; grep -rn "from sqlalchemy" app/routers/ --include="*.py" | grep -v deps.py | grep -v __pycache__
```

期望输出为空（或仅 deps.py 中的 AsyncSession 类型导入）。

- [ ] **Step 3: 验证应用启动**

```bash
cd backend; uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

启动后访问 `http://localhost:8000/docs` 确认 OpenAPI schema 完整。

- [ ] **Step 4: 更新 AGENTS.md**

在 AGENTS.md 的「2. 目录结构」中添加 `repositories/` 目录描述。更新「架构分层」表格，增加 Repository 层说明。

- [ ] **Step 5: 提交**

```bash
git add -A
git commit -m "refactor: 后端三层架构重构完成 — Router→Service→Repository"
```
