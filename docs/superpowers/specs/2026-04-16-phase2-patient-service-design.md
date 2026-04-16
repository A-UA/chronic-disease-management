# 第二期：全栈 Patient Service (患者服务) 微服务设计规范 (Phase 2.1)

> 创建日期：2026-04-16
> 状态：已确认并进行中

## 1. 业务目标与定位

本阶段属于微服务重构计划的 **Phase 2.1**，其核心是在已有的 Java 和 NestJS 平台底层 `Auth + Gateway` 的基础设施之上，搭建真正处理繁重复合业务逻辑的 **Patient Service（患者服务）**。

其承载的业务包含以下 5 大主轴，且需要 **同时在 Java (Spring Boot) 和 NestJS 环境中分别提供全功能对等实现**：
1. `patients`: 患者档案中心（承载基础信息、以及基于 JSONB 结构的既往病史与门诊记录）
2. `health_metrics`: 多维度体征监护（对录入的血压、血糖、心率、BMI 记录提供自动超限警告演算机制）
3. `patient_family_links`: 家属网络（负责打通家属代理权限和跨组织挂载关系）
4. `patient_manager_assignments`: 责任追踪系统（区分 Main 管理师与 Assistant 管理师架构）
5. `management_suggestions`: 诊疗干预指令系统（流转临床指南和生活行动指南）

## 2. “JWT 级联”式授权与多租户隔离架构 (Auth & Identity)

为了应对多层级部门下探获取下属病人信息，并适应基于连接池复用的 ORM（Hibernate 与 TypeORM），本阶段完全 **抛弃数据库底层的 PostgreSQL RLS 注入**（即避开 `SET LOCAL`），转向更为可控、完全无状态的网关隔离方案。

### 2.1 网关 Auth 扩展：发放 `allowed_org_ids`
原有的 `Gateway -> Auth Service` 签发 JWT 的行为需增加如下环节：
1. **树结构溯源**：当用户请求 `/login` 或 `/switch-org` 并获取最终 `access_token` 前，Auth 服务需要主动递归向下查询当前目标 `orgId` 的所有子孙节点。
2. **结构塞入 JWT**：将其结果（如 `[24, 25, 29]`）以 `allowed_org_ids` 的数组字段形式序列化编码到 JWT payload。

### 2.2 共享实体调整
- 在共享核心组件下（`@cdm/shared` 库和 Java 的 `IdentityPayload`），新增必填属性：
  ```typescript
  // NestJS 侧
  export interface IdentityPayload {
    userId: number;
    tenantId: number;
    orgId: number;
    allowedOrgIds: number[];
    roles: string[];
  }
  ```

### 2.3 扁平化“软” RLS 实现限制准则
从现在起，所有 `patient-service` 层面对数据表造成的 SELECT / UPDATE / DELETE 流量，在编译成 SQL 的最终时刻，都**必须带有租户及可见范围的切片判断**：
```sql
WHERE tenant_id = :tenantId AND org_id IN (:allowedOrgIds) 
```
*注：不再具有 RLS 的魔法隐藏，开发时需要在 Java `@Query` 或 TypeORM `QueryBuilder/FindOptions` 中显式附加上述条件或通过 AOP 拦截修改条件树。*

## 3. Java 架构图谱

* **运行端口**: `8020` (HTTP)
* **连接模式**: 经由 Java Gateway (8000) 的 Spring Cloud Gateway 规则 `/api/v1/patients/**`、`/api/v1/health-metrics/**` 等转发。
* **分层抽象**:
  * `Entity`: 基于 JPA 声明患者与业务相关的 5 个基础实体，利用 `@MappedSuperclass` 维护一致审计追踪 (`createdAt`, `updatedAt`)。
  * `Repository`: `JpaRepository<Patients, Long>`，在其内强制方法参数注入 `Tenant ID` 及其扩展边界。
  * `Service`: 容纳核心业务：例如 `HealthMetricService` 在提交后实时验证阈值。
  * `Controller`: 基础 Web 模块点，承接携带 `X-Identity` 自定义内部 Header 并解析利用。

## 4. NestJS 架构图谱

* **运行端口**: `8021` (基于 `@nestjs/microservices` 的 TCP 通道)
* **连接模式**: Nodejs 应用在 Nest 体系的 Gateway (8001) 接受 HTTP，经由内部专属代理（如 `PatientProxyController`）下沉传递。
* **分层抽象**:
  * `Entity`: TypeORM Entity 定义，支持针对 JSON 字段进行特化抽取。
  * `Controller (@MessagePattern)`: 注册 TCP 事件响应监听，比如 `@MessagePattern({ cmd: 'patient_create' })`。
  * `Service`: 处理并验证数据有效性，在 ORM Option 边界上严格防穿透。

## 5. 升级实操蓝图与步骤

1. **Step 1: 基础设施改写（Auth扩容）**
   - 修正 Java: 更新 Auth Service 登录与机构选择节点代码，增加下级部门抓取函数，补充至 Token claims。
   - 修正 NestJS: 更新微服务器 Auth 模块对应生成与解析行为。
2. **Step 2: 构建 Java 端 Patient Microservice 本体**
   - 从新建 maven submodule `patient-service` 开始。
   - 实体建模 -> 仓储绑定 -> 业务编写。集成 JWT 头部提取网守。
3. **Step 3: 构建 NestJS 端 Patient Microservice 本体**
   - 在 pnpm workspace 创建子服务 `patient-service`。
   - 配置 TypeORM 映射 -> TCP 控制器响应 -> 网关层透传 HTTP 发送节点暴露。
4. **Step 4: 测试集成** 
   - 前后端对齐通信接口及 Token 解析包容度，完成双向业务的横向 CRUD 可读。
