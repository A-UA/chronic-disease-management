# 三层架构重构实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `app/modules/` + `app/core/` + `app/db/` + `app/api/` 重组为 `routers/` + `services/` + `ai/` + `base/` + `models/` 五层架构，零 API 变更。

**Architecture:** 底层 base（基础设施）+ models（ORM）→ 中层 services（业务编排）+ ai（AI 领域）→ 顶层 routers（HTTP 适配器）。依赖严格单向，禁止反向。

**Tech Stack:** FastAPI, SQLAlchemy 2.x Async, PostgreSQL, arq, Alembic

**Spec:** `docs/superpowers/specs/2026-04-07-three-layer-architecture-design.md`

---

### Task 1: 创建目录骨架

**Files:**
- Create: `app/base/__init__.py`
- Create: `app/models/__init__.py` (临时空文件，后续 git mv 覆盖)
- Create: `app/routers/__init__.py` (临时空文件，后续 git mv 覆盖)
- Create: `app/routers/deps.py` (临时空文件)
- Create: `app/routers/auth/__init__.py`
- Create: `app/routers/audit/__init__.py`
- Create: `app/routers/patient/__init__.py`
- Create: `app/routers/system/__init__.py`
- Create: `app/routers/rag/__init__.py`
- Create: `app/services/__init__.py`
- Create: `app/services/auth/__init__.py`
- Create: `app/services/audit/__init__.py`
- Create: `app/services/patient/__init__.py`
- Create: `app/services/system/__init__.py`
- Create: `app/services/rag/__init__.py`
- Create: `app/ai/__init__.py`
- Create: `app/ai/rag/__init__.py`
- Create: `app/ai/agent/__init__.py`

- [ ] **Step 1: 创建 base、services、ai 顶级包**

```powershell
cd d:\codes\chronic-disease-management\backend
mkdir app\base; New-Item app\base\__init__.py -Force
mkdir app\services; New-Item app\services\__init__.py -Force
mkdir app\ai; New-Item app\ai\__init__.py -Force
```

- [ ] **Step 2: 创建 services 子目录**

```powershell
cd d:\codes\chronic-disease-management\backend
mkdir app\services\auth; New-Item app\services\auth\__init__.py -Force
mkdir app\services\audit; New-Item app\services\audit\__init__.py -Force
mkdir app\services\patient; New-Item app\services\patient\__init__.py -Force
mkdir app\services\system; New-Item app\services\system\__init__.py -Force
mkdir app\services\rag; New-Item app\services\rag\__init__.py -Force
```

- [ ] **Step 3: 创建 ai 子目录**

```powershell
cd d:\codes\chronic-disease-management\backend
mkdir app\ai\rag; New-Item app\ai\rag\__init__.py -Force
mkdir app\ai\agent; New-Item app\ai\agent\__init__.py -Force
```

- [ ] **Step 4: 创建 routers 子目录（不创建 routers/__init__.py，Task 4 会 git mv 过来）**

```powershell
cd d:\codes\chronic-disease-management\backend
mkdir app\routers\auth; New-Item app\routers\auth\__init__.py -Force
mkdir app\routers\audit; New-Item app\routers\audit\__init__.py -Force
mkdir app\routers\patient; New-Item app\routers\patient\__init__.py -Force
mkdir app\routers\system; New-Item app\routers\system\__init__.py -Force
mkdir app\routers\rag; New-Item app\routers\rag\__init__.py -Force
```

- [ ] **Step 5: Commit 骨架**

```powershell
cd d:\codes\chronic-disease-management\backend
git add app\base app\services app\ai app\routers
git commit -m "refactor: 创建三层架构目录骨架 (routers/services/ai/base)"
```

---

### Task 2: 迁移 base 层（core/ → base/，db/session.py → base/database.py）

**Files:**
- Move: `app/core/config.py` → `app/base/config.py`
- Move: `app/core/security.py` → `app/base/security.py`
- Move: `app/core/exceptions.py` → `app/base/exceptions.py`
- Move: `app/core/middleware.py` → `app/base/middleware.py`
- Move: `app/core/snowflake.py` → `app/base/snowflake.py`
- Move: `app/core/storage.py` → `app/base/storage.py`
- Move: `app/db/session.py` → `app/base/database.py`

- [ ] **Step 1: 移动 core 全部文件到 base**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\core\config.py app\base\config.py
git mv app\core\security.py app\base\security.py
git mv app\core\exceptions.py app\base\exceptions.py
git mv app\core\middleware.py app\base\middleware.py
git mv app\core\snowflake.py app\base\snowflake.py
git mv app\core\storage.py app\base\storage.py
```

- [ ] **Step 2: 移动 db/session.py → base/database.py**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\db\session.py app\base\database.py
```

- [ ] **Step 3: 修复 base 内部的自引用 import**

`app/base/security.py` 内部引用了 `from app.core.config`，需改为 `from app.base.config`：

```python
# app/base/security.py: 将
from app.core.config import settings
# 改为
from app.base.config import settings
```

`app/base/storage.py` 内部引用了 `from app.core.config`，需改为 `from app.base.config`：

```python
# app/base/storage.py: 将
from app.core.config import settings
# 改为
from app.base.config import settings
```

`app/base/database.py`（原 session.py）内部引用了 `from app.core.config`，需改为 `from app.base.config`：

```python
# app/base/database.py: 将
from app.core.config import settings
# 改为
from app.base.config import settings
```

- [ ] **Step 4: Commit**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "refactor: core/ → base/, db/session.py → base/database.py"
```

---

### Task 3: 迁移 models 层（db/models/ → models/）

**Files:**
- Move: `app/db/models/` 全部 15 个文件 → `app/models/`

- [ ] **Step 1: 移动全部 model 文件**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\db\models\__init__.py app\models\__init__.py
git mv app\db\models\base.py app\models\base.py
git mv app\db\models\user.py app\models\user.py
git mv app\db\models\tenant.py app\models\tenant.py
git mv app\db\models\organization.py app\models\organization.py
git mv app\db\models\rbac.py app\models\rbac.py
git mv app\db\models\menu.py app\models\menu.py
git mv app\db\models\patient.py app\models\patient.py
git mv app\db\models\health_metric.py app\models\health_metric.py
git mv app\db\models\manager.py app\models\manager.py
git mv app\db\models\knowledge.py app\models\knowledge.py
git mv app\db\models\chat.py app\models\chat.py
git mv app\db\models\audit.py app\models\audit.py
git mv app\db\models\settings.py app\models\settings.py
git mv app\db\models\api_key.py app\models\api_key.py
```

- [ ] **Step 2: 修复 models 内部的 import**

`app/models/base.py` 引用了 `from app.core.snowflake`，需改为：

```python
# app/models/base.py: 将
from app.core.snowflake import generate_id
# 改为
from app.base.snowflake import generate_id
```

所有 model 文件（organization.py, rbac.py, tenant.py, user.py, manager.py, patient.py, health_metric.py, knowledge.py, chat.py, audit.py, api_key.py, menu.py, settings.py）中引用 `from app.db.models.base` 的，改为 `from app.models.base`。同理 model 之间的交叉引用 `from app.db.models.xxx` 改为 `from app.models.xxx`。

逐文件检查并修复所有 `app.db.models` → `app.models` 的内部引用。

- [ ] **Step 3: 修复 models/__init__.py 的 import**

`app/models/__init__.py` 中引用了 `from app.db.models.xxx`，全部改为 `from app.models.xxx`：

```python
# 示例：将所有
from app.db.models.base import Base  # noqa
from app.db.models.user import User  # noqa
# 改为
from app.models.base import Base  # noqa
from app.models.user import User  # noqa
# ... 以此类推
```

- [ ] **Step 4: Commit**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "refactor: db/models/ → models/ 提升为顶级包"
```

---

### Task 4: 迁移 routers 基座（api/ → routers/）

**Files:**
- Move: `app/api/api.py` → `app/routers/__init__.py`
- Move: `app/api/deps.py` → `app/routers/deps.py`

- [ ] **Step 1: 移动 api.py 为 routers 的 __init__.py**

```powershell
cd d:\codes\chronic-disease-management\backend
# 删除骨架创建的空 __init__.py（如果存在）
Remove-Item app\routers\__init__.py -ErrorAction SilentlyContinue
git mv app\api\api.py app\routers\__init__.py
```

- [ ] **Step 2: 移动 deps.py**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\api\deps.py app\routers\deps.py
```

- [ ] **Step 3: 修复 routers/deps.py 内部 import**

```python
# app/routers/deps.py: 将
from app.core.config import settings
from app.core.security import ALGORITHM
# 改为
from app.base.config import settings
from app.base.security import ALGORITHM
```

同一文件中所有 `from app.db.models` 改为 `from app.models`，`from app.db.session` 改为 `from app.base.database`。

- [ ] **Step 4: routers/__init__.py 暂时保留旧 import 路径**

此时 modules/ 尚未迁移，`routers/__init__.py` 中的 `from app.modules.xxx` 路径暂时保留，Task 5-10 迁移时逐步更新。

- [ ] **Step 5: Commit**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "refactor: api/ → routers/ (deps.py + 路由注册)"
```

---

### Task 5: 迁移 auth + audit 模块

**Files:**
- Move: `app/modules/auth/router.py` → `app/routers/auth/router.py`
- Move: `app/modules/auth/email.py` → `app/services/auth/email.py`
- Move: `app/modules/audit/router.py` → `app/routers/audit/router.py`
- Move: `app/modules/audit/service.py` → `app/services/audit/service.py`

- [ ] **Step 1: 迁移 auth 模块**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\modules\auth\router.py app\routers\auth\router.py
git mv app\modules\auth\email.py app\services\auth\email.py
```

- [ ] **Step 2: 修复 routers/auth/router.py 的 import**

```python
# 将所有
from app.core.config import settings       →  from app.base.config import settings
from app.core.security import ...          →  from app.base.security import ...
from app.core.exceptions import ...        →  from app.base.exceptions import ...
from app.api.deps import ...               →  from app.routers.deps import ...
from app.db.models import ...              →  from app.models import ...
from app.modules.auth.email import ...     →  from app.services.auth.email import ...
from app.modules.system.quota import ...   →  from app.services.system.quota import ...
```

- [ ] **Step 3: 修复 services/auth/email.py 的 import**

```python
# 将
from app.core.config import settings       →  from app.base.config import settings
```

- [ ] **Step 4: 创建 routers/auth/__init__.py re-export**

```python
# app/routers/auth/__init__.py
from app.routers.auth.router import router  # noqa: F401
```

- [ ] **Step 5: 迁移 audit 模块**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\modules\audit\router.py app\routers\audit\router.py
git mv app\modules\audit\service.py app\services\audit\service.py
```

- [ ] **Step 6: 修复 routers/audit/router.py 的 import**

```python
from app.api.deps import ...               →  from app.routers.deps import ...
from app.db.models import ...              →  from app.models import ...
from app.modules.audit.service import ...  →  from app.services.audit.service import ...
# 以及所有 app.core → app.base
```

- [ ] **Step 7: 修复 services/audit/service.py 的 import**

```python
from app.db.models.audit import AuditLog   →  from app.models.audit import AuditLog
from app.core.snowflake import ...         →  from app.base.snowflake import ...
```

- [ ] **Step 8: 创建 routers/audit/__init__.py re-export**

```python
# app/routers/audit/__init__.py
from app.routers.audit.router import router  # noqa: F401
```

- [ ] **Step 9: 更新 routers/__init__.py 中 auth + audit 的 import 路径**

```python
# app/routers/__init__.py: 将
from app.modules.audit.router import router as audit_logs_router
from app.modules.auth.router import router as auth_router
# 改为
from app.routers.audit import router as audit_logs_router
from app.routers.auth import router as auth_router
```

- [ ] **Step 10: Commit**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "refactor: 迁移 auth + audit 模块到 routers/services"
```

---

### Task 6: 迁移 patient 模块

**Files:**
- Move: `app/modules/patient/router_patients.py` → `app/routers/patient/patients.py`
- Move: `app/modules/patient/router_health_metrics.py` → `app/routers/patient/health_metrics.py`
- Move: `app/modules/patient/router_family.py` → `app/routers/patient/family.py`
- Move: `app/modules/patient/router_managers.py` → `app/routers/patient/managers.py`
- Move: `app/modules/patient/health_alert.py` → `app/services/patient/health_alert.py`

- [ ] **Step 1: 移动文件**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\modules\patient\router_patients.py app\routers\patient\patients.py
git mv app\modules\patient\router_health_metrics.py app\routers\patient\health_metrics.py
git mv app\modules\patient\router_family.py app\routers\patient\family.py
git mv app\modules\patient\router_managers.py app\routers\patient\managers.py
git mv app\modules\patient\health_alert.py app\services\patient\health_alert.py
```

- [ ] **Step 2: 修复 4 个 router 文件的 import**

对 `patients.py`、`health_metrics.py`、`family.py`、`managers.py` 逐个修复：

```python
from app.core.* import ...                 →  from app.base.* import ...
from app.api.deps import ...               →  from app.routers.deps import ...
from app.db.models import ...              →  from app.models import ...
from app.modules.patient.health_alert import ...  →  from app.services.patient.health_alert import ...
from app.modules.system.* import ...       →  # 暂保留，Task 8 迁移 system 时更新
```

- [ ] **Step 3: 修复 services/patient/health_alert.py 的 import**

```python
from app.core.config import settings       →  from app.base.config import settings
from app.db.models import ...              →  from app.models import ...
```

- [ ] **Step 4: 更新 routers/__init__.py 中 patient 的 import 路径**

```python
# 将
from app.modules.patient.router_family import router as family_router
from app.modules.patient.router_health_metrics import router as health_metrics_router
from app.modules.patient.router_managers import router as managers_router
from app.modules.patient.router_patients import router as patients_router
# 改为
from app.routers.patient.family import router as family_router
from app.routers.patient.health_metrics import router as health_metrics_router
from app.routers.patient.managers import router as managers_router
from app.routers.patient.patients import router as patients_router
```

- [ ] **Step 5: Commit**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "refactor: 迁移 patient 模块到 routers/services"
```

---

### Task 7: 迁移 system 模块

**Files:**
- Move: 10 个 router 文件 → `app/routers/system/`（去 `router_` 前缀）
- Move: `app/modules/system/quota.py` → `app/services/system/quota.py`
- Move: `app/modules/system/rbac.py` → `app/services/system/rbac.py`
- Move: `app/modules/system/settings_service.py` → `app/services/system/settings.py`

- [ ] **Step 1: 移动 10 个 router 文件**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\modules\system\router_api_keys.py app\routers\system\api_keys.py
git mv app\modules\system\router_dashboard.py app\routers\system\dashboard.py
git mv app\modules\system\router_external_api.py app\routers\system\external_api.py
git mv app\modules\system\router_menus.py app\routers\system\menus.py
git mv app\modules\system\router_organizations.py app\routers\system\organizations.py
git mv app\modules\system\router_rbac.py app\routers\system\rbac.py
git mv app\modules\system\router_settings.py app\routers\system\settings.py
git mv app\modules\system\router_tenants.py app\routers\system\tenants.py
git mv app\modules\system\router_usage.py app\routers\system\usage.py
git mv app\modules\system\router_users.py app\routers\system\users.py
```

- [ ] **Step 2: 移动 3 个 service 文件**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\modules\system\quota.py app\services\system\quota.py
git mv app\modules\system\rbac.py app\services\system\rbac.py
git mv app\modules\system\settings_service.py app\services\system\settings.py
```

- [ ] **Step 3: 修复全部 10 个 router 文件的 import**

对 `api_keys.py`、`dashboard.py`、`external_api.py`、`menus.py`、`organizations.py`、`rbac.py`、`settings.py`、`tenants.py`、`usage.py`、`users.py` 逐个修固：

```python
from app.core.* import ...                 →  from app.base.* import ...
from app.api.deps import ...               →  from app.routers.deps import ...
from app.db.models import ...              →  from app.models import ...
from app.db.models.xxx import ...          →  from app.models.xxx import ...
from app.modules.system.quota import ...   →  from app.services.system.quota import ...
from app.modules.system.rbac import ...    →  from app.services.system.rbac import ...
from app.modules.system.settings_service import ... → from app.services.system.settings import ...
from app.modules.rag.* import ...          →  # 暂保留，Task 9 迁移 RAG 时更新
from app.modules.audit import ...          →  from app.services.audit.service import ...
```

- [ ] **Step 4: 修复 3 个 service 文件的 import**

对 `quota.py`、`rbac.py`、`settings.py`：

```python
from app.core.config import settings       →  from app.base.config import settings
from app.db.models import ...              →  from app.models import ...
from app.db.models.xxx import ...          →  from app.models.xxx import ...
```

- [ ] **Step 5: 更新 routers/__init__.py 中 system 的 import 路径**

```python
# 将
from app.modules.system.router_api_keys import router as api_keys_router
from app.modules.system.router_dashboard import router as dashboard_router
from app.modules.system.router_external_api import router as external_api_router
from app.modules.system.router_menus import router as menus_router
from app.modules.system.router_organizations import router as organizations_router
from app.modules.system.router_rbac import router as rbac_router
from app.modules.system.router_settings import router as settings_router
from app.modules.system.router_tenants import router as tenants_router
from app.modules.system.router_usage import router as usage_router
from app.modules.system.router_users import router as users_router
# 改为
from app.routers.system.api_keys import router as api_keys_router
from app.routers.system.dashboard import router as dashboard_router
from app.routers.system.external_api import router as external_api_router
from app.routers.system.menus import router as menus_router
from app.routers.system.organizations import router as organizations_router
from app.routers.system.rbac import router as rbac_router
from app.routers.system.settings import router as settings_router
from app.routers.system.tenants import router as tenants_router
from app.routers.system.usage import router as usage_router
from app.routers.system.users import router as users_router
```

- [ ] **Step 6: Commit**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "refactor: 迁移 system 模块到 routers/services"
```

---

### Task 8: 迁移 RAG 模块（最复杂，三向拆分）

**Files:**
- Move: 4 个 router → `app/routers/rag/`
- Move: schemas.py, tasks.py → `app/services/rag/`
- Move: 13 个 AI 文件 → `app/ai/rag/`
- Delete: `app/modules/rag/chat_service.py`（重复代码，拆解归并）
- Delete: `app/modules/rag/models.py`（re-export 不再需要）

- [ ] **Step 1: 移动 4 个 router 文件**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\modules\rag\router_chat.py app\routers\rag\chat.py
git mv app\modules\rag\router_conversations.py app\routers\rag\conversations.py
git mv app\modules\rag\router_documents.py app\routers\rag\documents.py
git mv app\modules\rag\router_knowledge_bases.py app\routers\rag\knowledge_bases.py
```

- [ ] **Step 2: 移动 service 文件**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\modules\rag\schemas.py app\services\rag\schemas.py
git mv app\modules\rag\tasks.py app\services\rag\tasks.py
```

- [ ] **Step 3: 移动 13 个 AI 计算文件到 ai/rag/**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\modules\rag\retrieval.py app\ai\rag\retrieval.py
git mv app\modules\rag\citation.py app\ai\rag\citation.py
git mv app\modules\rag\context.py app\ai\rag\context.py
git mv app\modules\rag\compress.py app\ai\rag\compress.py
git mv app\modules\rag\query_rewrite.py app\ai\rag\query_rewrite.py
git mv app\modules\rag\evaluation.py app\ai\rag\evaluation.py
git mv app\modules\rag\ingestion.py app\ai\rag\ingestion.py
git mv app\modules\rag\ingestion_legacy.py app\ai\rag\ingestion_legacy.py
git mv app\modules\rag\embeddings.py app\ai\rag\embeddings.py
git mv app\modules\rag\embedding_validation.py app\ai\rag\embedding_validation.py
git mv app\modules\rag\document_parser.py app\ai\rag\document_parser.py
git mv app\modules\rag\llm_legacy.py app\ai\rag\llm_legacy.py
git mv app\modules\rag\reranker_legacy.py app\ai\rag\reranker_legacy.py
```

- [ ] **Step 4: 删除不再需要的文件**

```powershell
cd d:\codes\chronic-disease-management\backend
git rm app\modules\rag\models.py
# chat_service.py 暂保留，Task 11 拆解后删除
```

- [ ] **Step 5: 修复 4 个 router 文件的 import**

对 `chat.py`、`conversations.py`、`documents.py`、`knowledge_bases.py`：

```python
from app.core.* import ...                     →  from app.base.* import ...
from app.api.deps import ...                   →  from app.routers.deps import ...
from app.db.models import ...                  →  from app.models import ...
from app.db.session import AsyncSessionLocal   →  from app.base.database import AsyncSessionLocal
from app.modules.rag.retrieval import ...      →  from app.ai.rag.retrieval import ...
from app.modules.rag.citation import ...       →  from app.ai.rag.citation import ...
from app.modules.rag.context import ...        →  from app.ai.rag.context import ...
from app.modules.rag.chat_service import ...   →  from app.ai.rag.retrieval import ...
from app.modules.rag.tasks import ...          →  from app.services.rag.tasks import ...
from app.modules.system.quota import ...       →  from app.services.system.quota import ...
from app.modules.agent import ...              →  from app.ai.agent import ...
```

- [ ] **Step 6: 修复 13 个 ai/rag/ 文件的 import**

对所有 `ai/rag/*.py`：

```python
from app.core.config import settings           →  from app.base.config import settings
from app.db.models import ...                  →  from app.models import ...
from app.db.session import AsyncSessionLocal   →  from app.base.database import AsyncSessionLocal
from app.modules.rag.query_rewrite import ...  →  from app.ai.rag.query_rewrite import ...
from app.modules.rag.ingestion_legacy import ...  →  from app.ai.rag.ingestion_legacy import ...
from app.modules.rag.embedding_validation import ... → from app.ai.rag.embedding_validation import ...
from app.modules.system.quota import ...       →  from app.services.system.quota import ...
```

- [ ] **Step 7: 修复 services/rag/tasks.py 的 import**

```python
from app.modules.rag.ingestion import process_document   →  from app.ai.rag.ingestion import process_document
from app.db.models.audit import AuditLog                 →  from app.models.audit import AuditLog
from app.db.session import AsyncSessionLocal              →  from app.base.database import AsyncSessionLocal
```

- [ ] **Step 8: 更新 routers/__init__.py 中 RAG 的 import 路径**

```python
# 将
from app.modules.rag.router_chat import router as chat_router
from app.modules.rag.router_conversations import router as conversations_router
from app.modules.rag.router_documents import router as documents_router
from app.modules.rag.router_knowledge_bases import router as kb_router
# 改为
from app.routers.rag.chat import router as chat_router
from app.routers.rag.conversations import router as conversations_router
from app.routers.rag.documents import router as documents_router
from app.routers.rag.knowledge_bases import router as kb_router
```

- [ ] **Step 9: Commit**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "refactor: 迁移 RAG 模块到 routers/services/ai 三层"
```

---

### Task 9: 迁移 agent 模块（→ ai/agent/）

**Files:**
- Move: `app/modules/agent/__init__.py` → `app/ai/agent/__init__.py`（覆盖骨架）
- Move: `app/modules/agent/graph.py` → `app/ai/agent/graph.py`
- Move: `app/modules/agent/memory.py` → `app/ai/agent/memory.py`
- Move: `app/modules/agent/security.py` → `app/ai/agent/security.py`
- Move: `app/modules/agent/state.py` → `app/ai/agent/state.py`
- Move: `app/modules/agent/skills/` → `app/ai/agent/skills/`

- [ ] **Step 1: 移动 agent 主文件**

```powershell
cd d:\codes\chronic-disease-management\backend
# 覆盖骨架 __init__.py
Remove-Item app\ai\agent\__init__.py
git mv app\modules\agent\__init__.py app\ai\agent\__init__.py
git mv app\modules\agent\graph.py app\ai\agent\graph.py
git mv app\modules\agent\memory.py app\ai\agent\memory.py
git mv app\modules\agent\security.py app\ai\agent\security.py
git mv app\modules\agent\state.py app\ai\agent\state.py
```

- [ ] **Step 2: 移动 skills 子目录**

```powershell
cd d:\codes\chronic-disease-management\backend
mkdir app\ai\agent\skills -Force
git mv app\modules\agent\skills\__init__.py app\ai\agent\skills\__init__.py
git mv app\modules\agent\skills\base.py app\ai\agent\skills\base.py
git mv app\modules\agent\skills\rag_skill.py app\ai\agent\skills\rag_skill.py
git mv app\modules\agent\skills\patient_skills.py app\ai\agent\skills\patient_skills.py
git mv app\modules\agent\skills\calculator_skills.py app\ai\agent\skills\calculator_skills.py
git mv app\modules\agent\skills\markdown_loader.py app\ai\agent\skills\markdown_loader.py
```

如果存在 `custom/` 子目录：
```powershell
git mv app\modules\agent\skills\custom app\ai\agent\skills\custom
```

- [ ] **Step 3: 修复 agent 全部文件的 import**

对 `ai/agent/` 下所有文件：

```python
from app.modules.agent.* import ...            →  from app.ai.agent.* import ...
from app.modules.rag.* import ...              →  from app.ai.rag.* import ...
from app.core.config import settings           →  from app.base.config import settings
from app.db.models import ...                  →  from app.models import ...
```

具体文件：
- `__init__.py`：`from app.modules.agent.graph` → `from app.ai.agent.graph`
- `graph.py`：`from app.modules.agent.state` → `from app.ai.agent.state`，`from app.modules.agent.memory` → `from app.ai.agent.memory`
- `memory.py`：`from app.core.config` → `from app.base.config`
- `skills/base.py`：`from app.modules.agent.security` → `from app.ai.agent.security`
- `skills/rag_skill.py`：`from app.modules.rag.retrieval` → `from app.ai.rag.retrieval`
- `skills/patient_skills.py`：`from app.db.models` → `from app.models`
- `skills/__init__.py`、`skills/markdown_loader.py`：逐个检查 `app.modules` 引用

- [ ] **Step 4: Commit**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "refactor: 迁移 agent 模块到 ai/agent"
```

---

### Task 10: 迁移 seed + 清理旧目录

**Files:**
- Move: `app/db/seed_data.py` → `app/seed.py`
- Delete: `app/modules/` 整个目录
- Delete: `app/db/` 整个目录（剩余文件已全部迁走）
- Delete: `app/api/` 整个目录
- Delete: `app/core/` 整个目录

- [ ] **Step 1: 移动 seed_data.py**

```powershell
cd d:\codes\chronic-disease-management\backend
git mv app\db\seed_data.py app\seed.py
```

- [ ] **Step 2: 修复 seed.py 的 import**

```python
# app/seed.py: 将
from app.db.models.menu import Menu                     →  from app.models.menu import Menu
from app.db.models.rbac import Action, Permission, ...  →  from app.models.rbac import Action, Permission, ...
from app.db.session import AsyncSessionLocal as ...     →  from app.base.database import AsyncSessionLocal as ...
from app.db.models.organization import ...              →  from app.models.organization import ...
from app.db.models.tenant import Tenant                 →  from app.models.tenant import Tenant
from app.db.models.user import User                     →  from app.models.user import User
from app.core.security import get_password_hash         →  from app.base.security import get_password_hash
from app.core.snowflake import ...                     →  from app.base.snowflake import ...
```

- [ ] **Step 3: 清理旧 modules __init__.py 残留 + 旧目录**

```powershell
cd d:\codes\chronic-disease-management\backend
# 删除 modules 下残留的 __init__.py 文件
git rm app\modules\auth\__init__.py -f 2>$null
git rm app\modules\audit\__init__.py -f 2>$null
git rm app\modules\patient\__init__.py -f 2>$null
git rm app\modules\system\__init__.py -f 2>$null
git rm app\modules\rag\__init__.py -f 2>$null
git rm app\modules\rag\chat_service.py -f 2>$null

# 清理空目录（git 不跟踪空目录，但本地需清理）
Remove-Item app\modules -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item app\db -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item app\api -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item app\core -Recurse -Force -ErrorAction SilentlyContinue
```

- [ ] **Step 4: Commit**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "refactor: 迁移 seed.py，删除旧 modules/db/api/core 目录"
```

---

### Task 11: 更新外部引用（main.py、worker.py、alembic）

**Files:**
- Modify: `app/main.py`
- Modify: `app/tasks/worker.py`
- Modify: `alembic/env.py`
- Modify: `app/telemetry/setup.py`
- Modify: `app/plugins/registry.py`
- Modify: `app/plugins/llm/openai_compatible.py`
- Modify: `app/plugins/embedding/openai_compatible.py`
- Modify: `app/plugins/reranker/openai_compatible.py`

- [ ] **Step 1: 修复 main.py**

```python
# app/main.py: 关键行修改

# 将
from app.api.api import api_router
from app.core.config import settings
# 改为
from app.routers import api_router
from app.base.config import settings

# 将（health_check 函数内）
from app.db.session import AsyncSessionLocal
from app.modules.system.quota import get_redis_client
# 改为
from app.base.database import AsyncSessionLocal
from app.services.system.quota import get_redis_client

# 将
from app.core.middleware import RequestIDMiddleware
# 改为
from app.base.middleware import RequestIDMiddleware
```

- [ ] **Step 2: 修复 tasks/worker.py**

检查 `app/tasks/worker.py` 中所有 `from app.modules` 和 `from app.core` 引用并修复：

```python
from app.core.config import settings           →  from app.base.config import settings
from app.modules.rag.tasks import ...          →  from app.services.rag.tasks import ...
```

- [ ] **Step 3: 修复 alembic/env.py**

```python
# alembic/env.py: 将
from app.core.config import settings
from app.db.models import Base
# 改为
from app.base.config import settings
from app.models import Base
```

- [ ] **Step 4: 修复 telemetry/setup.py**

```python
from app.core.config import settings           →  from app.base.config import settings
```

- [ ] **Step 5: 修复 plugins/ 下的文件**

对 `plugins/registry.py`、`plugins/llm/openai_compatible.py`、`plugins/embedding/openai_compatible.py`、`plugins/reranker/openai_compatible.py`：

```python
from app.core.config import settings           →  from app.base.config import settings
```

- [ ] **Step 6: Commit**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "refactor: 更新 main/worker/alembic/plugins 的 import 路径"
```

---

### Task 12: 全局残留扫描 + 验证

**Files:**
- 无新文件，只做验证和修复

- [ ] **Step 1: 扫描残留的旧 import 路径**

逐一搜索以下模式，发现就修复：

```powershell
cd d:\codes\chronic-disease-management\backend
# 搜索残留引用
Select-String -Path "app\**\*.py" -Pattern "from app\.core\." -Recurse
Select-String -Path "app\**\*.py" -Pattern "from app\.db\." -Recurse
Select-String -Path "app\**\*.py" -Pattern "from app\.api\." -Recurse
Select-String -Path "app\**\*.py" -Pattern "from app\.modules\." -Recurse
```

预期输出：**全部为零结果**。如有残留，逐个修复。

- [ ] **Step 2: Python 语法校验（import 通过）**

```powershell
cd d:\codes\chronic-disease-management\backend
uv run python -c "from app.main import app; print('✅ Import OK')"
```

预期输出：`✅ Import OK`

- [ ] **Step 3: 启动服务验证路由注册**

```powershell
cd d:\codes\chronic-disease-management\backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

在另一个终端验证：
```powershell
Invoke-RestMethod http://localhost:8000/health
```

预期：返回 `{"status": "ok", ...}`

然后访问 `http://localhost:8000/docs` 确认所有 18 个路由端点均正常注册。

- [ ] **Step 4: 验证 Alembic**

```powershell
cd d:\codes\chronic-disease-management\backend
uv run alembic check
```

预期：无迁移差异。

- [ ] **Step 5: 验证 seed**

```powershell
cd d:\codes\chronic-disease-management\backend
uv run python -c "from app.seed import main; print('✅ Seed import OK')"
```

- [ ] **Step 6: Commit + 打 tag**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "refactor: 三层架构重构完成，全部 import 验证通过"
git tag v0.9.0-three-layer-arch
```

---

### Task 13: 更新项目文档

**Files:**
- Modify: `GEMINI.md`（即 AGENTS.md）

- [ ] **Step 1: 更新 GEMINI.md 中的目录结构**

将 GEMINI.md 第 2 节「目录结构」中的旧结构替换为新的三层架构目录树（与 spec 文档第 4 节一致）。

- [ ] **Step 2: 更新 GEMINI.md 中的开发约定**

更新后端开发约定部分：
- 将 `modules/` 相关描述改为 `routers/` + `services/` + `ai/`
- 将 `core/` 引用改为 `base/`
- 将 `db/` 引用改为 `models/` 和 `base/database`
- 更新种子数据命令：`python -m app.seed`

- [ ] **Step 3: Commit**

```powershell
cd d:\codes\chronic-disease-management\backend
git add -A
git commit -m "docs: 更新 GEMINI.md 目录结构和开发约定"
```
