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
*   **全局配置 (代替散落的注解)**：不使用 `@TableId(type = IdType.ASSIGN_ID)` 和 `@TableLogic` 注解，而是采用诸如若依、芋道等大型开源项目中流行的全局配置方案。在 `application.yml` 的 `mybatis-plus.global-config.db-config` 中统一配置 `id-type: assign_id` 以及 `logic-delete-field`，保持实体类的极度整洁。

### 3.3 数据流与类型边界 (Data Flow & Type Safety)
得益于项目中已存在的 `JacksonAutoConfiguration`（已配置 `ToStringSerializer`），我们不再需要在代码里手动做 String 和 Long 的互相转换（推翻初版繁琐设计），而是采用最彻底的 Java 行业最佳实践：
1.  **全栈类型统一**：在 Java 端（Entity、所有入站 DTO、所有出站 VO），涉及的所有 ID 字段统统修正为 `Long`。
2.  **出站响应给前端 (JSON)**：由 `JacksonAutoConfiguration` 全局拦截，自动将 VO 中的 `Long` 转换为前端所需的 `String`，完美规避精度丢失。
3.  **入站接收前端数据 (JSON)**：Jackson 原生支持自动将前端传来的 JSON 字符串（如 `{"id": "12345"}`）安全地反序列化回 DTO 中的 `Long` 字段。
如此一来，Java 核心代码内将只有高效的 `Long` 在流转，且代码极其清爽，没有任何类型强制转换的性能损耗，这也是为什么该类已经存在于您的代码库中的原因。

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
