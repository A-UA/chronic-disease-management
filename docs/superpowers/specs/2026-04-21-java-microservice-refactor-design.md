# Java 微服务架构行业标准化整改 — 设计规格

> **项目**: chronic-disease-management / backend-java
> **日期**: 2026-04-21
> **状态**: 已批准

---

## 1. 目标

将当前 Java 微服务后端从原型阶段提升至**行业公认标准架构**，对标 RuoYi-Cloud / 阿里巴巴 Java 开发手册规范。覆盖：架构分层、命名标准、代码质量、服务治理、可观测性等全维度。

## 2. 版本锁定

| 组件 | 当前版本 | 目标版本 |
|------|---------|---------|
| Spring Boot | 3.4.4 | **3.5.13** |
| Spring Cloud | 2024.0.1 | **2025.0.1** |
| Spring Cloud Alibaba | 无 | **2025.0.0.0** |
| Nacos Server | 无 | **2.4.3+** |
| Sa-Token | 1.40.0 | 1.40.0（不变） |
| Java | 17 | 17（不变） |

## 3. 模块命名与目录结构

采用 `cdm-{module}` 统一前缀命名法。

| 当前目录 | → 新目录 | artifactId | 端口 |
|---------|---------|-----------|------|
| pom.xml（父） | - | `cdm-parent` | - |
| common-lib/ | `cdm-common/` | `cdm-common` | -（库） |
| gateway/ | `cdm-gateway/` | `cdm-gateway` | 8001 |
| auth-service/ | `cdm-auth/` | `cdm-auth` | 8011 |
| patient-service/ | `cdm-patient/` | `cdm-patient` | 8021 |
| _(不存在)_ | `cdm-ai/` | `cdm-ai` | 8031 |

### 目录树

```
backend-java/
├── pom.xml                          # cdm-parent
├── cdm-common/
│   └── src/main/java/com/cdm/common/
│       ├── config/                  # JacksonAutoConfiguration, WebMvcAutoConfiguration
│       ├── domain/                  # Result<T>, ResultCode, BaseEntity
│       ├── exception/               # BusinessException, GlobalExceptionHandler
│       ├── security/                # SecurityContextHolder, SecurityUtils, HeaderInterceptor, IdentityContext
│       ├── feign/                   # FeignRequestInterceptor
│       └── util/                    # SnowflakeIdGenerator
├── cdm-gateway/
│   └── src/main/java/com/cdm/gateway/
│       ├── config/                  # SaTokenConfig, IgnoreWhiteProperties, GatewayConfig
│       ├── filter/                  # AuthFilter
│       └── handler/                 # GatewayExceptionHandler
├── cdm-auth/
│   └── src/main/java/com/cdm/auth/
│       ├── controller/
│       ├── dto/                     # LoginDto, RegisterDto, SelectOrgDto, SwitchOrgDto
│       ├── vo/                      # LoginVo, UserVo, MenuVo, OrganizationVo
│       ├── entity/
│       ├── repository/
│       ├── service/
│       └── security/               # StpInterfaceImpl
├── cdm-patient/
│   └── src/main/java/com/cdm/patient/
│       ├── controller/
│       ├── dto/
│       ├── vo/
│       ├── entity/
│       ├── repository/
│       └── service/
└── cdm-ai/
    └── src/main/java/com/cdm/ai/
        ├── controller/
        ├── dto/
        ├── vo/
        ├── entity/
        ├── repository/
        ├── service/
        └── client/                  # AgentClient (OpenFeign)
```

## 4. cdm-common 公共基础层

### 4.1 统一响应体

```java
// com.cdm.common.domain.Result<T>
public class Result<T> {
    private int code;
    private String message;
    private T data;

    public static <T> Result<T> ok(T data);
    public static <T> Result<T> ok();
    public static <T> Result<T> fail(ResultCode code);
    public static <T> Result<T> fail(ResultCode code, String msg);
    public static <T> Result<T> fail(int code, String msg);
}
```

```java
// com.cdm.common.domain.ResultCode
public enum ResultCode {
    SUCCESS(200, "操作成功"),
    BAD_REQUEST(400, "请求参数错误"),
    UNAUTHORIZED(401, "未登录或令牌已过期"),
    FORBIDDEN(403, "无此权限"),
    NOT_FOUND(404, "资源不存在"),
    VALIDATION_ERROR(422, "参数校验失败"),
    INTERNAL_ERROR(500, "服务器内部错误");
}
```

规则：所有 Controller 返回类型统一为 `Result<XxxVo>`，禁止裸返回 Entity 或 Map。

### 4.2 统一异常体系

```java
// com.cdm.common.exception.BusinessException
public class BusinessException extends RuntimeException {
    private final ResultCode resultCode;
    // 工厂方法: notFound(), forbidden(), validation(), badRequest(), internal()
}

// com.cdm.common.exception.GlobalExceptionHandler
@RestControllerAdvice
public class GlobalExceptionHandler {
    // BusinessException          → Result.fail(e.getResultCode())
    // MethodArgumentNotValidException → Result.fail(422, 字段级错误拼接)
    // ConstraintViolationException    → Result.fail(422, ...)
    // HttpMessageNotReadableException → Result.fail(400, "请求体格式错误")
    // Exception (兜底)               → Result.fail(500, "服务器内部错误") + 日志
}
```

通过 `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` 自动装配。

### 4.3 三层身份模式（RuoYi 标准）

链路：`Gateway AuthFilter → HeaderInterceptor → SecurityContextHolder → SecurityUtils`

**SecurityContextHolder**：基于 TransmittableThreadLocal 存储身份上下文。

```java
public class SecurityContextHolder {
    private static final TransmittableThreadLocal<Map<String, Object>> CONTEXT = new TransmittableThreadLocal<>();
    public static void set(String key, Object value);
    public static <T> T get(String key, Class<T> clazz);
    public static void remove();
}
```

**SecurityUtils**：业务代码零样板获取身份。

```java
public class SecurityUtils {
    public static String getUserId();
    public static String getTenantId();
    public static String getOrgId();
    public static List<String> getRoles();
    public static List<String> getAllowedOrgIds();
}
```

**HeaderInterceptor**：自动从 HTTP Header 提取身份存入 ThreadLocal。

```java
public class HeaderInterceptor implements AsyncHandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest request, ...) {
        SecurityContextHolder.set("userId", request.getHeader("X-User-Id"));
        SecurityContextHolder.set("tenantId", request.getHeader("X-Tenant-Id"));
        SecurityContextHolder.set("orgId", request.getHeader("X-Org-Id"));
        SecurityContextHolder.set("roles", request.getHeader("X-Roles"));
        SecurityContextHolder.set("allowedOrgIds", request.getHeader("X-Allowed-Org-Ids"));
        return true;
    }

    @Override
    public void afterCompletion(...) {
        SecurityContextHolder.remove();
    }
}
```

**FeignRequestInterceptor**：Feign 调用时自动透传身份 Header。

```java
public class FeignRequestInterceptor implements RequestInterceptor {
    @Override
    public void apply(RequestTemplate template) {
        template.header("X-User-Id", SecurityUtils.getUserId());
        template.header("X-Tenant-Id", SecurityUtils.getTenantId());
        template.header("X-Org-Id", SecurityUtils.getOrgId());
    }
}
```

### 4.4 雪花 ID 生成器

```java
@Component
public class SnowflakeIdGenerator {
    private static final Snowflake SNOWFLAKE = IdUtil.getSnowflake(1, 1);
    public String nextId() { return String.valueOf(SNOWFLAKE.nextId()); }
    public static String generateId() { return String.valueOf(SNOWFLAKE.nextId()); }
}
```

返回 String 类型，对齐 AGENTS.md 规范。

### 4.5 BaseEntity

```java
@MappedSuperclass @Getter @Setter
public abstract class BaseEntity {
    @Id @Column(columnDefinition = "bigint")
    private String id;
    @CreationTimestamp @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;
    @UpdateTimestamp @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
```

### 4.6 pom.xml 依赖

```xml
<dependencies>
    <dependency>spring-boot-starter-web</dependency>
    <dependency>spring-boot-starter-validation</dependency>
    <dependency>hutool-core</dependency>
    <dependency>lombok</dependency>
    <dependency>transmittable-thread-local</dependency>
</dependencies>
```

## 5. cdm-gateway 网关层

### 5.1 AuthFilter（RuoYi 标准模式）

- 白名单可配置（IgnoreWhiteProperties 从 yml 读取）
- 安全清洗：先清除伪造 Header，再注入真实值
- `getOrder() = -200`（高优先级）

### 5.2 GatewayExceptionHandler

实现 ErrorWebExceptionHandler，@Order(-1)，统一返回 `{"code":xxx, "message":"...", "data":null}`。

### 5.3 路由（Nacos 服务发现）

```yaml
routes:
  - id: cdm-auth
    uri: lb://cdm-auth
    predicates: Path=/api/v1/auth/**, /api/v1/users/**, ...
  - id: cdm-patient
    uri: lb://cdm-patient
    predicates: Path=/api/v1/patients/**, /api/v1/health-metrics/**, ...
  - id: cdm-ai
    uri: lb://cdm-ai
    predicates: Path=/api/v1/kb/**, /api/v1/documents/**, /api/v1/conversations/**
```

### 5.4 pom.xml 依赖

```xml
spring-cloud-starter-gateway
spring-cloud-starter-alibaba-nacos-discovery
spring-cloud-starter-loadbalancer
sa-token-reactor-spring-boot3-starter
sa-token-jwt
springdoc-openapi-starter-webflux-ui
```

网关基于 WebFlux，不依赖 cdm-common。

## 6. cdm-auth 认证微服务

### 整改清单

- Map<String, Object> 返回 → LoginVo / UserVo / MenuVo / OrganizationVo
- 手动 new IdentityContext → SecurityUtils
- BCryptPasswordEncoder 直接实例化 → @Bean 注入
- 冗余 SnowflakeIdGenerator → 删除，用 cdm-common
- BaseEntity → 迁移至 cdm-common
- 修复 register() 中 TenantEntity 未落库 Bug
- 新增 SpringDoc 注解

## 7. cdm-patient 患者微服务

### 整改清单

- 剥离 AI 域代码（KnowledgeBase、Document、AgentClient、MinioService）到 cdm-ai
- X-Identity-Base64 方案 → SecurityUtils
- 裸返回 Entity → Result<PatientVo>
- @RequestParam 散装参数 → @Valid @RequestBody CreatePatientDto
- RuntimeException → BusinessException
- 手写 getter/setter → Lombok + BaseEntity

## 8. cdm-ai AI 微服务（新建）

### 职责

知识库 + 文档管理 + 会话/消息管理。对标 NestJS apps/ai。

### 核心设计

- 全生命周期删除编排：Agent 向量清理 → MinIO 文件删除 → DB 删除
- 硬编码 tenantId=1L → SecurityUtils.getTenantId()
- AgentClient 改为 OpenFeign 声明式调用

## 9. Nacos 集成

### 各微服务 bootstrap.yml

```yaml
spring:
  application:
    name: cdm-auth
  cloud:
    nacos:
      server-addr: ${NACOS_ADDR:localhost:8848}
      discovery:
        namespace: ${NACOS_NAMESPACE:}
        group: CDM_GROUP
      config:
        namespace: ${NACOS_NAMESPACE:}
        group: CDM_GROUP
        file-extension: yml
        shared-configs:
          - data-id: cdm-common.yml
            group: CDM_GROUP
            refresh: true
```

### 配置分层

| Data ID | 作用域 | 内容 |
|---------|-------|------|
| cdm-common.yml | 全局 | 数据库、Jackson、日志 |
| cdm-gateway.yml | 网关 | SaToken、路由、白名单 |
| cdm-auth.yml | 认证 | JWT 密钥 |
| cdm-patient.yml | 患者 | 服务特有 |
| cdm-ai.yml | AI | MinIO、Agent URL |

### Docker Compose

```yaml
nacos:
  image: nacos/nacos-server:v2.4.3
  environment: MODE=standalone, NACOS_AUTH_ENABLE=false
  ports: 8848:8848, 9848:9848
```

## 10. 跨切面能力

- **OpenFeign**：声明式服务调用 + FeignRequestInterceptor 身份透传
- **SpringDoc**：各微服务 `@Tag` / `@Operation`，网关聚合
- **Micrometer Tracing**：链路追踪，日志含 traceId
- **Actuator**：健康检查 `/actuator/health`
- **多环境配置**：application.yml + application-dev.yml + application-prod.yml

## 11. 需同步更新

- AGENTS.md：端口、版本、启动命令
- docker-compose.yml：新增 Nacos
- database/init.sql：如有变更
