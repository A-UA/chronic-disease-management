# cdm-auth MyBatis-Plus 重构设计文档

## 1. 目标 (Goal)
将 `cdm-auth` 微服务及底层依赖彻底从 Spring Data JPA 迁移至 MyBatis-Plus。同时，将 Java 实体类的 ID 从 `String` 修正为更为标准和高效的 `Long`（长整型），并通过转换机制确保与前端接口和 `AGENTS.md` 规范的完美兼容。

## 2. 作用范围 (Scope)
由于这是涉及核心框架层面的巨大变更，本期工程仅限定在 `cdm-auth` 微服务及其前置通用模块 `cdm-common` 中执行。

## 3. 架构与组件变更 (Architecture & Components)

### 3.1 依赖层 (Dependencies)
*   **清理**：在 `cdm-parent`、`cdm-common`、`cdm-auth` 的 `pom.xml` 中剔除 `spring-boot-starter-data-jpa`。
*   **引入**：在 `cdm-parent` 中添加 `mybatis-plus-spring-boot3-starter`。

### 3.2 实体类规范纠正 (Entity & Domain)
*   **BaseEntity 升级**：将 `cdm-common` 下的 `BaseEntity` 中的 `private String id` 更改为 `private Long id`。
*   **ORM 注解更替**：
    *   移除所有的 `@Entity`, `@Table`, `@Column`, `@Id`。
    *   引入 `@TableName`。
    *   在 `id` 上标注 `@TableId(type = IdType.ASSIGN_ID)`，激活 MyBatis-Plus 原生的 64 位雪花算法生成器。
*   **逻辑删除**：对诸如 `is_deleted` 的字段补充 `@TableLogic` 注解。

### 3.3 数据流与类型边界 (Data Flow & Type Safety)
针对 `AGENTS.md` 规定的“入站出站参数 ID 皆为 String”的要求，确立明确的数据转换边界：
1.  **前端与 Controller 交互 (入站 DTO & 出站 VO)**：维持 ID 类型为 `String` 不变，确保外部 API 契约不破损。
2.  **业务逻辑与数据库交互 (Service & Entity)**：实体层 `Entity` 强制采用 `Long`。
3.  **转换边界**：所有的 `String` 到 `Long` 的互相转化，严格收拢在 Service 层的组装阶段以及各实体类现有的 `toVo(Entity entity)` 方法内部处理，例如：`vo.setId(String.valueOf(entity.getId()))`。

### 3.4 数据访问层 (Repository -> Mapper)
*   彻底删除所有现存的 `JpaRepository` 接口（如 `UserRepository`、`MenuRepository` 等）。
*   全面建立 MyBatis-Plus 标准 Mapper 层，所有新接口统一继承 `BaseMapper<T>` 并挂载 `@Mapper` 注解。

### 3.5 业务逻辑层适配 (Service Layer)
*   改造现有的核心 Service（如 `UserServiceImpl`），使其继承 MyBatis-Plus 的 `ServiceImpl<Mapper, Entity>` 并实现框架的 `IService<Entity>`。
*   将原有的 JPA 推导查询语法（如 `findByEmail`、`existsByEmail`）替换为 `LambdaQueryWrapper` 流式查询。
*   将带有 `@Query` 注解的复杂查询（如多条件 `OR` 判断）直接重写为等价的 MyBatis-Plus 构造器链式代码。

## 4. 异常处理与测试 (Error Handling & Testing)
*   由于移除了 JPA，原有的 Hibernate 事务拦截可能失效，需确认 Spring Boot 内置的 JDBC 事务（`@Transactional`）顺利接管。
*   针对 `cdm-auth` 内部关于用户、权限、租户的核心增删改查场景，重构后需确保所有涉及 ID 的查询条件不会因为 `String` 与 `Long` 的混用而发生 `ClassCastException`。
