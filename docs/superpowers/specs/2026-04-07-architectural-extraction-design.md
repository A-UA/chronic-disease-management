# 架构演进：六边形大网关融合与 AI 引擎拆分 (Radical BFF Consolidation & AI Engine Extraction)

**状态**: 规划完成，准备实施
**日期**: 2026-04-07

## 1. 目标 (Objective)

执行一次“地狱级”的深度架构重构。打破原有的 20 多个散落路由碎片，强制合并为 4 个巨大的 Backend-For-Frontend (BFF) 六边形网关（Gateways）。同时，将 AI 的认知层彻底脱开业务外壳，沉淀为独立的 `app/engine/`。

## 2. 核心挑战与约束 (Constraints)

- 必须对原先的 20 余个 `router_*.py` 实施级别合并融合，消除冗余依赖。
- 确保测试套件 (234 测试) 在全盘路径切断重启后能够被系统性修复（修正 Mock 路径与 imports）。
- `app/modules` 和 `app/engine` 彻底禁止出现 `APIRouter`。全网只有一个网络层。

## 3. 架构设计蓝图 (Architecture)

### 3.1 三级物理目录重塑与融合拓扑

1. **`app/api/gateways/` (BFF 网络大网关)**
   接管所有 API，强制合并收敛为 4 把钥匙：
   - `admin_api.py`: 缝合 `system` 目录下所有的租户、计费、配额、组织、用户、菜单、RBAC，以及 `audit` 审计路由。
   - `clinic_api.py`: 缝合 `patient` 目录下所有的患者档案、监控指标、家属绑定、管理师分配路由。
   - `ai_api.py`: 缝合 `rag` 目录下的流式聊天、文档注入、知识库管理路由。
   - `auth_api.py`: 独占 `auth` 相关路由，处理令牌下发。

2. **`app/engine/` (AI 认知推理核心层)**
   - 彻底剥离出 `rag` 与 `agent`，作为不包含 HTTP 逻辑的纯正 Python 计算引擎区。
   - 暴露确定的 `async def execute_xxx()` 等执行器给 `ai_api.py` 调用。

3. **`app/modules/` (传统确定性业务领域层/无脑区)**
   - 全被扒光 Web 外壳的 `patient`、`system`、`auth`、`audit` 内核服务区。

## 4. 行动计划 (Phasing)

- **阶段 1：核心抽离 (Extract Engine)**
  - 创建 `app/engine/rag` 与 `app/engine/agent`，并转移核心状态机与混合检索引擎。
- **阶段 2：网关熔铸 (Cast the Gateways)**
  - 新建 `app/api/gateways/` 并建立四扇大门。将 20 余个分散的 router 内容暴力组装并去重。
- **阶段 3：废墟清理 (Clear the Debris)**
  - 斩断 `modules/` 下的旧 router 文件。
  - 重写 `app/api/api.py`（总接线板）。
- **阶段 4：伤口缝合与校验 (Heal & Test)**
  - 全局替换 `tests/` 和业务里由于强行切断路由造成的依赖断裂。修复 234 测试底线。
