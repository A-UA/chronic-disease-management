# 多租户递归组织架构与系统核心修复设计文档

## 1. 背景与目标
本项目目前在多租户隔离、ID 精度保护以及系统架构健壮性方面存在若干阻塞性问题。为了支持“租户下有不同组织”的业务需求，并修复现有的 Bug，本方案旨在建立一套支持无限层级的组织树架构，并全面规范前后端的 ID 处理逻辑。

### 核心目标
- **架构扩展**：将 `organizations` 改造为递归树形结构，支持“租户-分公司-组织-部门”层级。
- **权限增强**：实现“租户超管”逻辑，允许其管理所属根组织及其所有子组织的数据。
- **系统修复**：解决测试套件导入错误、Dashboard 逻辑失效、RLS 策略不健壮等 P0/P1 Bug。
- **精度保护**：全面统一前后端雪花 ID 为字符串处理，彻底消除 JS 精度丢失。

## 2. 详细设计

### 2.1 数据库架构变更 (Database)
- **`organizations` 表**：
    - 新增 `parent_id: BigInteger`，外键关联 `organizations.id`，`ondelete='CASCADE'`。
    - 建立自关联关系，支持递归查询。
- **RLS 策略优化**：
    - 修改所有表的 RLS 策略，将 `current_setting('app.current_org_id')::bigint` 统一改为 `current_setting('app.current_org_id', true)::bigint`。
    - 增加对“父组织访问子组织数据”的支持（通过递归检查或业务层注入 ID 列表）。

### 2.2 后端逻辑重构 (Backend)
- **依赖项 (`app/api/deps.py`)**：
    - 补全 `get_current_active_user`（作为 `get_current_user` 的别名并增加 `is_active` 状态检查）。
    - 优化 `get_current_org_user`：如果用户在根组织拥有 `admin/owner` 角色，则标记为“租户超管”，并在上下文中允许穿透访问子组织。
- **Dashboard (`app/api/endpoints/dashboard.py`)**：
    - 统计 SQL 引入 **Recursive CTE**：
      ```sql
      WITH RECURSIVE org_tree AS (
          SELECT id FROM organizations WHERE id = :target_org_id
          UNION ALL
          SELECT o.id FROM organizations o INNER JOIN org_tree ot ON o.parent_id = ot.id
      )
      SELECT ... FROM ... WHERE org_id IN (SELECT id FROM org_tree);
      ```
    - 修复模型属性引用错误（从 `OrganizationUser` 获取角色而非 `User`）。
- **全局异常处理 (`app/main.py`)**：
    - 统一使用 `SnowflakeJSONResponse` 返回所有错误响应，确保高性能序列化和大整数安全。

### 2.3 前端类型对齐 (Frontend)
- **TypeScript 类型定义**：
    - 全面扫描 `src/services/api/`，将所有 `id`, `orgId`, `userId`, `patientId` 等字段的类型从 `number` 改为 `string`。
- **状态管理**：
    - 确保 `localStorage` 存储的 `currentOrgId` 以字符串形式处理。
    - 在 Ant Design 表格、下拉框等组件中，Key 值统一使用字符串 ID。

### 2.4 测试套件恢复 (Testing)
- **路径修复**：修正 `tests/` 下所有过时的模块导入路径（如 `app.api.endpoints.admin` -> `app.api.endpoints`）。
- **依赖适配**：更新测试中的 `Mock` 逻辑，确保适配最新的 RBAC 依赖项。

## 3. 风险评估
- **递归性能**：如果组织层级过深，递归查询可能存在性能瓶颈。由于本项目主要面向医疗机构，层级通常在 3-5 层以内，CTE 性能足以应对。
- **数据迁移**：现有组织数据需要平滑过渡到树形结构（默认 `parent_id` 为 NULL）。

## 4. 验收标准
1. `uv run python -m pytest` 能够成功启动并运行（允许部分由于环境导致的逻辑失败，但不能有导入错误）。
2. Dashboard `/stats` 接口能够正确返回所属租户及其下属组织的汇总统计。
3. 前端界面能够正确显示雪花 ID 且无控制台精度丢失报警。
4. Postgres RLS 策略在未设置组织上下文时不再抛出异常。
