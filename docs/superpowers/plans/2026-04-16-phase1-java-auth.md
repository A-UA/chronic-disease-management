# 第一期-子计划B：Java Spring Boot Gateway + Auth Service 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 Java Spring Boot 微服务集群的 Gateway（8000）和 auth-service（8010），实现完整的登录链路，使前端能通过 Java 后端完成登录、获取用户信息和菜单树。

**Architecture:** Gateway 使用 Spring Cloud Gateway + Sa-Token Reactor，负责路由拦截和令牌校验。auth-service 是独立的 Spring Boot 应用，使用 Sa-Token JWT 无状态模式签发令牌。Gateway 校验通过后将身份信息注入 HTTP Header 转发给下游服务。

**Tech Stack:** Java 17+, Spring Boot 3.x, Spring Cloud Gateway, Sa-Token (JWT Stateless), Spring Data JPA, Maven, PostgreSQL 16

**设计文档:** `docs/superpowers/specs/2026-04-16-microservice-architecture-design.md`

**前置依赖:** 子计划 A 已完成（docker-compose.yml 中 PostgreSQL 已就绪）

**Sa-Token JWT 无状态模式说明：**
- 使用 `StpLogicJwtForStateless`，令牌信息全部编码在 JWT 中，不依赖 Redis
- 登录时通过 `SaLoginConfig.setExtra()` 将 `tenant_id`、`org_id`、`roles` 写入 JWT Payload
- 后续通过 `StpUtil.getExtra("tenant_id")` 读取，无需数据库/缓存查询
- 多部门选择流程使用 `SaTempUtil` 生成一次性临时令牌

---

## 文件结构

```
backend-java/
├── pom.xml                                        # 父 POM
├── .gitignore
│
├── gateway/
│   ├── pom.xml
│   └── src/main/
│       ├── java/com/cdm/gateway/
│       │   ├── GatewayApplication.java
│       │   └── config/
│       │       └── SaTokenConfig.java             # Sa-Token 路由拦截 + Header 注入
│       └── resources/
│           └── application.yml
│
└── auth-service/
    ├── pom.xml
    └── src/main/
        ├── java/com/cdm/auth/
        │   ├── AuthServiceApplication.java
        │   ├── config/                            # 配置层
        │   │   └── SaTokenConfig.java
        │   ├── controller/                        # 控制器层（HTTP 适配）
        │   │   └── AuthController.java
        │   ├── service/                           # 服务层（业务编排）
        │   │   ├── AuthService.java
        │   │   └── MenuService.java
        │   ├── repository/                        # 数据访问层
        │   │   ├── UserRepository.java
        │   │   ├── OrganizationRepository.java
        │   │   ├── OrganizationUserRepository.java
        │   │   ├── OrganizationUserRoleRepository.java
        │   │   ├── RoleRepository.java
        │   │   ├── PermissionRepository.java
        │   │   └── MenuRepository.java
        │   ├── entity/                            # 实体层（ORM 映射）
        │   │   ├── BaseEntity.java
        │   │   ├── UserEntity.java
        │   │   ├── TenantEntity.java
        │   │   ├── OrganizationEntity.java
        │   │   ├── OrganizationUserEntity.java
        │   │   ├── OrganizationUserRoleEntity.java
        │   │   ├── RoleEntity.java
        │   │   ├── PermissionEntity.java
        │   │   └── MenuEntity.java
        │   ├── dto/                               # 数据传输对象
        │   │   ├── LoginRequest.java
        │   │   ├── RegisterRequest.java
        │   │   ├── SelectOrgRequest.java
        │   │   ├── SwitchOrgRequest.java
        │   │   └── UserReadDto.java
        │   ├── security/                          # 安全/权限
        │   │   ├── StpInterfaceImpl.java
        │   │   └── IdentityContext.java
        │   ├── util/                              # 工具类
        │   │   └── SnowflakeIdGenerator.java
        │   └── exception/                         # 异常处理
        │       ├── BusinessException.java
        │       └── GlobalExceptionHandler.java
        └── resources/
            └── application.yml
```

---

## Task 1: 初始化 Maven 多模块项目

**Files:**
- Create: `backend-java/pom.xml`
- Create: `backend-java/gateway/pom.xml`
- Create: `backend-java/auth-service/pom.xml`
- Create: `backend-java/.gitignore`

- [ ] **Step 1: 创建父 POM（统一版本管理 + 模块声明）**

```xml
<!-- backend-java/pom.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.4.4</version>
        <relativePath/>
    </parent>

    <groupId>com.cdm</groupId>
    <artifactId>cdm-backend-java</artifactId>
    <version>0.1.0</version>
    <packaging>pom</packaging>
    <name>CDM Backend Java</name>

    <modules>
        <module>gateway</module>
        <module>auth-service</module>
    </modules>

    <properties>
        <java.version>17</java.version>
        <spring-cloud.version>2024.0.1</spring-cloud.version>
        <sa-token.version>1.40.0</sa-token.version>
    </properties>

    <dependencyManagement>
        <dependencies>
            <dependency>
                <groupId>org.springframework.cloud</groupId>
                <artifactId>spring-cloud-dependencies</artifactId>
                <version>${spring-cloud.version}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <dependencies>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-test</artifactId>
            <scope>test</scope>
        </dependency>
    </dependencies>
</project>
```

- [ ] **Step 2: 创建 gateway/pom.xml**

```xml
<!-- backend-java/gateway/pom.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.cdm</groupId>
        <artifactId>cdm-backend-java</artifactId>
        <version>0.1.0</version>
    </parent>

    <artifactId>gateway</artifactId>
    <name>CDM Gateway</name>

    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-starter-gateway</artifactId>
        </dependency>
        <dependency>
            <groupId>cn.dev33</groupId>
            <artifactId>sa-token-reactor-spring-boot3-starter</artifactId>
            <version>${sa-token.version}</version>
        </dependency>
        <dependency>
            <groupId>cn.dev33</groupId>
            <artifactId>sa-token-jwt</artifactId>
            <version>${sa-token.version}</version>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
```

- [ ] **Step 3: 创建 auth-service/pom.xml**

```xml
<!-- backend-java/auth-service/pom.xml -->
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
         https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.cdm</groupId>
        <artifactId>cdm-backend-java</artifactId>
        <version>0.1.0</version>
    </parent>

    <artifactId>auth-service</artifactId>
    <name>CDM Auth Service</name>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>cn.dev33</groupId>
            <artifactId>sa-token-spring-boot3-starter</artifactId>
            <version>${sa-token.version}</version>
        </dependency>
        <dependency>
            <groupId>cn.dev33</groupId>
            <artifactId>sa-token-jwt</artifactId>
            <version>${sa-token.version}</version>
        </dependency>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
                <configuration>
                    <excludes>
                        <exclude>
                            <groupId>org.projectlombok</groupId>
                            <artifactId>lombok</artifactId>
                        </exclude>
                    </excludes>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

- [ ] **Step 4: 创建 .gitignore**

```gitignore
# backend-java/.gitignore
target/
*.class
*.jar
.idea/
*.iml
.mvn/
```

- [ ] **Step 5: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-java/
git commit -m "feat(java): 初始化 Maven 多模块项目骨架（Sa-Token + Spring Cloud Gateway）"
```

---

## Task 2: Gateway — 应用入口 + Sa-Token 路由拦截

**Files:**
- Create: `backend-java/gateway/src/main/java/com/cdm/gateway/GatewayApplication.java`
- Create: `backend-java/gateway/src/main/java/com/cdm/gateway/config/SaTokenConfig.java`
- Create: `backend-java/gateway/src/main/resources/application.yml`

- [ ] **Step 1: 创建 Gateway 启动类**

```java
// backend-java/gateway/src/main/java/com/cdm/gateway/GatewayApplication.java
package com.cdm.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class GatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(GatewayApplication.class, args);
    }
}
```

- [ ] **Step 2: 创建 Sa-Token 配置（JWT 无状态 + 路由拦截 + Header 注入）**

```java
// backend-java/gateway/src/main/java/com/cdm/gateway/config/SaTokenConfig.java
package com.cdm.gateway.config;

import cn.dev33.satoken.jwt.StpLogicJwtForStateless;
import cn.dev33.satoken.reactor.filter.SaReactorFilter;
import cn.dev33.satoken.router.SaRouter;
import cn.dev33.satoken.stp.StpLogic;
import cn.dev33.satoken.stp.StpUtil;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Configuration
public class SaTokenConfig {

    @Bean
    @Primary
    public StpLogic getStpLogicJwt() {
        return new StpLogicJwtForStateless();
    }

    @Bean
    public SaReactorFilter getSaReactorFilter() {
        return new SaReactorFilter()
                .addInclude("/**")
                .addExclude(
                        "/api/v1/auth/login/access-token",
                        "/api/v1/auth/register",
                        "/api/v1/auth/select-org",
                        "/api/v1/auth/forgot-password",
                        "/api/v1/auth/reset-password"
                )
                .setAuth(obj -> {
                    SaRouter.match("/**", r -> StpUtil.checkLogin());
                });
    }

    @Bean
    public GlobalFilter identityHeaderFilter() {
        return (ServerWebExchange exchange, GatewayFilterChain chain) -> {
            if (!StpUtil.isLogin()) {
                return chain.filter(exchange);
            }

            String userId = String.valueOf(StpUtil.getLoginId());
            Object tenantId = StpUtil.getExtra("tenant_id");
            Object orgId = StpUtil.getExtra("org_id");
            Object roles = StpUtil.getExtra("roles");

            ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                    .header("X-User-Id", userId)
                    .header("X-Tenant-Id", tenantId != null ? String.valueOf(tenantId) : "")
                    .header("X-Org-Id", orgId != null ? String.valueOf(orgId) : "")
                    .header("X-Roles", roles != null ? String.valueOf(roles) : "")
                    .build();

            return chain.filter(exchange.mutate().request(mutatedRequest).build());
        };
    }
}
```

- [ ] **Step 3: 创建 Gateway 配置**

```yaml
# backend-java/gateway/src/main/resources/application.yml
server:
  port: 8000

sa-token:
  token-name: Authorization
  token-prefix: Bearer
  timeout: 604800
  jwt-secret-key: ${JWT_SECRET:your-jwt-secret-here-must-be-32-chars-long}
  is-read-header: true
  is-read-cookie: false
  is-print: false

spring:
  application:
    name: cdm-gateway
  cloud:
    gateway:
      routes:
        - id: auth-service
          uri: http://localhost:8010
          predicates:
            - Path=/api/v1/auth/**
```

- [ ] **Step 4: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-java/gateway/
git commit -m "feat(java): Gateway 应用 + Sa-Token JWT 无状态路由拦截"
```

---

## Task 3: Auth Service — 启动类 + 配置 + 实体层 + 异常处理

**Files:**
- Create: `auth-service/src/main/java/com/cdm/auth/AuthServiceApplication.java`
- Create: `auth-service/src/main/java/com/cdm/auth/config/SaTokenConfig.java`
- Create: `auth-service/src/main/java/com/cdm/auth/entity/*.java` (9 个实体)
- Create: `auth-service/src/main/java/com/cdm/auth/exception/*.java`
- Create: `auth-service/src/main/java/com/cdm/auth/security/IdentityContext.java`
- Create: `auth-service/src/main/resources/application.yml`

- [ ] **Step 1: 创建启动类**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/AuthServiceApplication.java
package com.cdm.auth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class AuthServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(AuthServiceApplication.class, args);
    }
}
```

- [ ] **Step 2: 创建 Sa-Token 配置**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/config/SaTokenConfig.java
package com.cdm.auth.config;

import cn.dev33.satoken.jwt.StpLogicJwtForStateless;
import cn.dev33.satoken.stp.StpLogic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

@Configuration
public class SaTokenConfig {
    @Bean
    @Primary
    public StpLogic getStpLogicJwt() {
        return new StpLogicJwtForStateless();
    }
}
```

- [ ] **Step 3: 创建实体基类**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/entity/BaseEntity.java
package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@MappedSuperclass
@Getter @Setter
public abstract class BaseEntity {
    @Id
    @Column(columnDefinition = "bigint")
    private Long id;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
```

- [ ] **Step 4: 创建实体类 — UserEntity, TenantEntity**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/entity/UserEntity.java
package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "users")
@Getter @Setter @NoArgsConstructor
public class UserEntity extends BaseEntity {

    @Column(unique = true, nullable = false, length = 255)
    private String email;

    @Column(name = "password_hash", length = 255)
    private String passwordHash;

    @Column(length = 255)
    private String name;
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/entity/TenantEntity.java
package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tenants")
@Getter @Setter @NoArgsConstructor
public class TenantEntity extends BaseEntity {

    @Column(nullable = false, length = 255)
    private String name;

    @Column(nullable = false, unique = true, length = 100)
    private String slug;

    @Column(name = "plan_type", length = 50)
    private String planType = "free";
}
```

- [ ] **Step 5: 创建实体类 — OrganizationEntity, OrganizationUserEntity, OrganizationUserRoleEntity**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/entity/OrganizationEntity.java
package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "organizations")
@Getter @Setter @NoArgsConstructor
public class OrganizationEntity extends BaseEntity {

    @Column(name = "tenant_id", nullable = false)
    private Long tenantId;

    @Column(name = "parent_id")
    private Long parentId;

    @Column(nullable = false, length = 255)
    private String name;

    @Column(nullable = false, length = 50)
    private String code;

    @Column(length = 20)
    private String status = "active";
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/entity/OrganizationUserEntity.java
package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.io.Serializable;

@Entity
@Table(name = "organization_users")
@IdClass(OrganizationUserEntity.PK.class)
@Getter @Setter @NoArgsConstructor
public class OrganizationUserEntity {

    @Id @Column(name = "org_id")
    private Long orgId;

    @Id @Column(name = "user_id")
    private Long userId;

    @Column(name = "tenant_id", nullable = false)
    private Long tenantId;

    @Column(name = "user_type", length = 20)
    private String userType = "staff";

    @Getter @Setter @NoArgsConstructor
    public static class PK implements Serializable {
        private Long orgId;
        private Long userId;
    }
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/entity/OrganizationUserRoleEntity.java
package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.io.Serializable;

@Entity
@Table(name = "organization_user_roles")
@IdClass(OrganizationUserRoleEntity.PK.class)
@Getter @Setter @NoArgsConstructor
public class OrganizationUserRoleEntity {

    @Id @Column(name = "org_id")
    private Long orgId;

    @Id @Column(name = "user_id")
    private Long userId;

    @Id @Column(name = "role_id")
    private Long roleId;

    @Column(name = "tenant_id", nullable = false)
    private Long tenantId;

    @Getter @Setter @NoArgsConstructor
    public static class PK implements Serializable {
        private Long orgId;
        private Long userId;
        private Long roleId;
    }
}
```

- [ ] **Step 6: 创建实体类 — RoleEntity, PermissionEntity, MenuEntity**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/entity/RoleEntity.java
package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "roles")
@Getter @Setter @NoArgsConstructor
public class RoleEntity extends BaseEntity {

    @Column(name = "tenant_id")
    private Long tenantId;

    @Column(name = "parent_role_id")
    private Long parentRoleId;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, length = 100)
    private String code;

    @Column(name = "is_system")
    private Boolean isSystem = false;

    @ManyToMany
    @JoinTable(name = "role_permissions",
        joinColumns = @JoinColumn(name = "role_id"),
        inverseJoinColumns = @JoinColumn(name = "permission_id"))
    private List<PermissionEntity> permissions = new ArrayList<>();
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/entity/PermissionEntity.java
package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "permissions")
@Getter @Setter @NoArgsConstructor
public class PermissionEntity extends BaseEntity {

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, unique = true, length = 100)
    private String code;

    @Column(name = "resource_id")
    private Long resourceId;

    @Column(name = "action_id")
    private Long actionId;
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/entity/MenuEntity.java
package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.util.Map;

@Entity
@Table(name = "menus")
@Getter @Setter @NoArgsConstructor
public class MenuEntity extends BaseEntity {

    @Column(name = "parent_id")
    private Long parentId;

    @Column(name = "tenant_id")
    private Long tenantId;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, unique = true, length = 100)
    private String code;

    @Column(name = "menu_type", nullable = false, length = 20)
    private String menuType = "page";

    @Column(length = 255)
    private String path;

    @Column(length = 50)
    private String icon;

    @Column(name = "permission_code", length = 100)
    private String permissionCode;

    @Column
    private Integer sort = 0;

    @Column(name = "is_visible")
    private Boolean isVisible = true;

    @Column(name = "is_enabled")
    private Boolean isEnabled = true;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Object> meta;
}
```

- [ ] **Step 7: 创建异常处理**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/exception/BusinessException.java
package com.cdm.auth.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

@Getter
public class BusinessException extends RuntimeException {
    private final HttpStatus status;
    private final String code;

    public BusinessException(HttpStatus status, String code, String message) {
        super(message);
        this.status = status;
        this.code = code;
    }

    public static BusinessException notFound(String msg) {
        return new BusinessException(HttpStatus.NOT_FOUND, "NOT_FOUND", msg);
    }

    public static BusinessException forbidden(String msg) {
        return new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN", msg);
    }

    public static BusinessException validation(String msg) {
        return new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", msg);
    }
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/exception/GlobalExceptionHandler.java
package com.cdm.auth.exception;

import cn.dev33.satoken.exception.NotLoginException;
import cn.dev33.satoken.exception.NotPermissionException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public ResponseEntity<Map<String, String>> handleBusiness(BusinessException ex) {
        return ResponseEntity.status(ex.getStatus())
                .body(Map.of("detail", ex.getMessage(), "code", ex.getCode()));
    }

    @ExceptionHandler(NotLoginException.class)
    public ResponseEntity<Map<String, String>> handleNotLogin(NotLoginException ex) {
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                .body(Map.of("detail", "未登录或令牌已过期", "code", "UNAUTHORIZED"));
    }

    @ExceptionHandler(NotPermissionException.class)
    public ResponseEntity<Map<String, String>> handleNotPermission(NotPermissionException ex) {
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
                .body(Map.of("detail", "无此权限: " + ex.getPermission(), "code", "FORBIDDEN"));
    }
}
```

- [ ] **Step 8: 创建 IdentityContext**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/security/IdentityContext.java
package com.cdm.auth.security;

import jakarta.servlet.http.HttpServletRequest;
import lombok.Getter;
import java.util.Arrays;
import java.util.List;

@Getter
public class IdentityContext {
    private final Long userId;
    private final Long tenantId;
    private final Long orgId;
    private final List<String> roles;

    public IdentityContext(HttpServletRequest request) {
        this.userId = parseLong(request.getHeader("X-User-Id"));
        this.tenantId = parseLong(request.getHeader("X-Tenant-Id"));
        this.orgId = parseLong(request.getHeader("X-Org-Id"));
        String rolesHeader = request.getHeader("X-Roles");
        this.roles = rolesHeader != null && !rolesHeader.isEmpty()
                ? Arrays.asList(rolesHeader.split(",")) : List.of();
    }

    private Long parseLong(String value) {
        if (value == null || value.isEmpty()) return null;
        try { return Long.parseLong(value); } catch (NumberFormatException e) { return null; }
    }
}
```

- [ ] **Step 9: 创建 application.yml**

```yaml
# backend-java/auth-service/src/main/resources/application.yml
server:
  port: 8010

sa-token:
  token-name: Authorization
  token-prefix: Bearer
  timeout: 604800
  jwt-secret-key: ${JWT_SECRET:your-jwt-secret-here-must-be-32-chars-long}
  is-read-header: true
  is-read-cookie: false
  is-print: false

spring:
  application:
    name: cdm-auth-service
  datasource:
    url: jdbc:postgresql://localhost:5432/ai_saas
    username: postgres
    password: postgres
    driver-class-name: org.postgresql.Driver
  jpa:
    hibernate:
      ddl-auto: validate
    show-sql: false
    properties:
      hibernate:
        dialect: org.hibernate.dialect.PostgreSQLDialect
        format_sql: true
```

- [ ] **Step 10: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-java/auth-service/
git commit -m "feat(java): auth-service 启动类 + 配置 + 9个实体 + 异常处理"
```

---

## Task 4: Auth Service — Repository 层

**Files:**
- Create: `auth-service/src/main/java/com/cdm/auth/repository/*.java`

- [ ] **Step 1: 创建所有 Repository 接口**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/repository/UserRepository.java
package com.cdm.auth.repository;

import com.cdm.auth.entity.UserEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface UserRepository extends JpaRepository<UserEntity, Long> {
    Optional<UserEntity> findByEmail(String email);
    boolean existsByEmail(String email);
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/repository/OrganizationRepository.java
package com.cdm.auth.repository;

import com.cdm.auth.entity.OrganizationEntity;
import org.springframework.data.jpa.repository.JpaRepository;

public interface OrganizationRepository extends JpaRepository<OrganizationEntity, Long> {
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/repository/OrganizationUserRepository.java
package com.cdm.auth.repository;

import com.cdm.auth.entity.OrganizationUserEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface OrganizationUserRepository
        extends JpaRepository<OrganizationUserEntity, OrganizationUserEntity.PK> {
    List<OrganizationUserEntity> findByUserId(Long userId);
    Optional<OrganizationUserEntity> findByOrgIdAndUserId(Long orgId, Long userId);
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/repository/OrganizationUserRoleRepository.java
package com.cdm.auth.repository;

import com.cdm.auth.entity.OrganizationUserRoleEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface OrganizationUserRoleRepository
        extends JpaRepository<OrganizationUserRoleEntity, OrganizationUserRoleEntity.PK> {
    List<OrganizationUserRoleEntity> findByOrgIdAndUserId(Long orgId, Long userId);
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/repository/RoleRepository.java
package com.cdm.auth.repository;

import com.cdm.auth.entity.RoleEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface RoleRepository extends JpaRepository<RoleEntity, Long> {
    Optional<RoleEntity> findByCodeAndTenantIdIsNull(String code);
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/repository/PermissionRepository.java
package com.cdm.auth.repository;

import com.cdm.auth.entity.PermissionEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;
import java.util.Set;

public interface PermissionRepository extends JpaRepository<PermissionEntity, Long> {
    @Query("SELECT p.code FROM PermissionEntity p JOIN p.roles r WHERE r.id IN :roleIds")
    Set<String> findCodesByRoleIds(List<Long> roleIds);
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/repository/MenuRepository.java
package com.cdm.auth.repository;

import com.cdm.auth.entity.MenuEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;

public interface MenuRepository extends JpaRepository<MenuEntity, Long> {
    @Query("SELECT m FROM MenuEntity m WHERE m.isEnabled = true " +
           "AND (m.tenantId IS NULL OR m.tenantId = :tenantId) ORDER BY m.sort ASC")
    List<MenuEntity> findActiveMenus(Long tenantId);
}
```

- [ ] **Step 2: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-java/auth-service/src/main/java/com/cdm/auth/repository/
git commit -m "feat(java): auth-service repository 数据访问层"
```

---

## Task 5: Auth Service — DTO + Service + Security + Controller

**Files:**
- Create: `auth-service/src/main/java/com/cdm/auth/dto/*.java`
- Create: `auth-service/src/main/java/com/cdm/auth/service/AuthService.java`
- Create: `auth-service/src/main/java/com/cdm/auth/service/MenuService.java`
- Create: `auth-service/src/main/java/com/cdm/auth/security/StpInterfaceImpl.java`
- Create: `auth-service/src/main/java/com/cdm/auth/util/SnowflakeIdGenerator.java`
- Create: `auth-service/src/main/java/com/cdm/auth/controller/AuthController.java`

- [ ] **Step 1: 创建 DTO 类**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/dto/LoginRequest.java
package com.cdm.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class LoginRequest {
    @Email @NotBlank
    private String username;
    @NotBlank
    private String password;
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/dto/RegisterRequest.java
package com.cdm.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class RegisterRequest {
    @Email @NotBlank
    private String email;
    @NotBlank
    private String password;
    private String name;
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/dto/SelectOrgRequest.java
package com.cdm.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class SelectOrgRequest {
    @NotNull
    private Long orgId;
    @NotBlank
    private String selectionToken;
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/dto/SwitchOrgRequest.java
package com.cdm.auth.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class SwitchOrgRequest {
    @NotNull
    private Long orgId;
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/dto/UserReadDto.java
package com.cdm.auth.dto;

import lombok.Builder;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data @Builder
public class UserReadDto {
    private Long id;
    private String email;
    private String name;
    private LocalDateTime createdAt;
    private Long tenantId;
    private Long orgId;
    private List<String> permissions;
}
```

- [ ] **Step 2: 创建 SnowflakeIdGenerator**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/util/SnowflakeIdGenerator.java
package com.cdm.auth.util;

import org.springframework.stereotype.Component;

@Component
public class SnowflakeIdGenerator {

    private static final long EPOCH = 1704067200000L;
    private static final long WORKER_BITS = 10L;
    private static final long SEQUENCE_BITS = 12L;
    private static final long MAX_SEQUENCE = (1L << SEQUENCE_BITS) - 1;

    private final long workerId = 1L;
    private long lastTimestamp = -1L;
    private long sequence = 0L;

    public synchronized long nextId() {
        long timestamp = System.currentTimeMillis();
        if (timestamp == lastTimestamp) {
            sequence = (sequence + 1) & MAX_SEQUENCE;
            if (sequence == 0) {
                while (timestamp <= lastTimestamp) {
                    timestamp = System.currentTimeMillis();
                }
            }
        } else {
            sequence = 0;
        }
        lastTimestamp = timestamp;
        return ((timestamp - EPOCH) << (WORKER_BITS + SEQUENCE_BITS))
                | (workerId << SEQUENCE_BITS) | sequence;
    }
}
```

- [ ] **Step 3: 创建 StpInterfaceImpl（Sa-Token 权限/角色回调）**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/security/StpInterfaceImpl.java
package com.cdm.auth.security;

import cn.dev33.satoken.stp.StpInterface;
import cn.dev33.satoken.stp.StpUtil;
import com.cdm.auth.entity.OrganizationUserRoleEntity;
import com.cdm.auth.entity.RoleEntity;
import com.cdm.auth.repository.OrganizationUserRoleRepository;
import com.cdm.auth.repository.PermissionRepository;
import com.cdm.auth.repository.RoleRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

@Component
@RequiredArgsConstructor
public class StpInterfaceImpl implements StpInterface {

    private final OrganizationUserRoleRepository orgUserRoleRepo;
    private final RoleRepository roleRepo;
    private final PermissionRepository permRepo;

    @Override
    public List<String> getPermissionList(Object loginId, String loginType) {
        Object orgIdObj = StpUtil.getExtra("org_id");
        if (orgIdObj == null) return List.of();
        Long userId = Long.parseLong(String.valueOf(loginId));
        Long orgId = Long.parseLong(String.valueOf(orgIdObj));

        var roleIds = orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId)
                .stream().map(OrganizationUserRoleEntity::getRoleId).collect(Collectors.toList());
        Set<Long> allRoleIds = expandRoleHierarchy(roleIds);
        if (allRoleIds.isEmpty()) return List.of();

        return new ArrayList<>(permRepo.findCodesByRoleIds(new ArrayList<>(allRoleIds)));
    }

    @Override
    public List<String> getRoleList(Object loginId, String loginType) {
        Object orgIdObj = StpUtil.getExtra("org_id");
        if (orgIdObj == null) return List.of();
        Long userId = Long.parseLong(String.valueOf(loginId));
        Long orgId = Long.parseLong(String.valueOf(orgIdObj));

        return orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId).stream()
                .map(our -> roleRepo.findById(our.getRoleId()).map(RoleEntity::getCode).orElse(null))
                .filter(Objects::nonNull).collect(Collectors.toList());
    }

    private Set<Long> expandRoleHierarchy(List<Long> roleIds) {
        Set<Long> all = new HashSet<>(roleIds);
        Queue<Long> queue = new LinkedList<>(roleIds);
        while (!queue.isEmpty()) {
            Long rid = queue.poll();
            roleRepo.findById(rid).ifPresent(role -> {
                if (role.getParentRoleId() != null && all.add(role.getParentRoleId())) {
                    queue.add(role.getParentRoleId());
                }
            });
        }
        return all;
    }
}
```

- [ ] **Step 4: 创建 MenuService**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/service/MenuService.java
package com.cdm.auth.service;

import com.cdm.auth.entity.MenuEntity;
import com.cdm.auth.repository.MenuRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
@RequiredArgsConstructor
public class MenuService {

    private final MenuRepository menuRepo;

    public List<Map<String, Object>> getMenuTree(Long tenantId, Set<String> permCodes) {
        var allMenus = menuRepo.findActiveMenus(tenantId);
        var visibleMenus = allMenus.stream()
                .filter(m -> m.getPermissionCode() == null
                        || m.getPermissionCode().isEmpty()
                        || permCodes.contains(m.getPermissionCode()))
                .toList();
        return buildTree(visibleMenus);
    }

    private List<Map<String, Object>> buildTree(List<MenuEntity> menus) {
        var menuMap = new LinkedHashMap<Long, Map<String, Object>>();
        for (var m : menus) {
            var node = new LinkedHashMap<String, Object>();
            node.put("id", m.getId());
            node.put("name", m.getName());
            node.put("code", m.getCode());
            node.put("menu_type", m.getMenuType());
            node.put("path", m.getPath());
            node.put("icon", m.getIcon());
            node.put("permission_code", m.getPermissionCode());
            node.put("sort", m.getSort());
            node.put("is_visible", m.getIsVisible());
            node.put("is_enabled", m.getIsEnabled());
            node.put("meta", m.getMeta());
            node.put("children", new ArrayList<Map<String, Object>>());
            menuMap.put(m.getId(), node);
        }

        var visibleIds = menuMap.keySet();
        var roots = new ArrayList<Map<String, Object>>();
        for (var m : menus) {
            var node = menuMap.get(m.getId());
            if (m.getParentId() != null && visibleIds.contains(m.getParentId())) {
                @SuppressWarnings("unchecked")
                var children = (List<Map<String, Object>>) menuMap.get(m.getParentId()).get("children");
                children.add(node);
            } else {
                roots.add(node);
            }
        }
        roots.removeIf(item -> "directory".equals(item.get("menu_type"))
                && ((List<?>) item.get("children")).isEmpty());
        return roots;
    }
}
```

- [ ] **Step 5: 创建 AuthService**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/service/AuthService.java
package com.cdm.auth.service;

import cn.dev33.satoken.stp.SaLoginConfig;
import cn.dev33.satoken.stp.StpUtil;
import cn.dev33.satoken.temp.SaTempUtil;
import com.cdm.auth.dto.UserReadDto;
import com.cdm.auth.entity.*;
import com.cdm.auth.exception.BusinessException;
import com.cdm.auth.repository.*;
import com.cdm.auth.util.SnowflakeIdGenerator;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepo;
    private final OrganizationRepository orgRepo;
    private final OrganizationUserRepository orgUserRepo;
    private final OrganizationUserRoleRepository orgUserRoleRepo;
    private final RoleRepository roleRepo;
    private final PermissionRepository permRepo;
    private final MenuService menuService;
    private final SnowflakeIdGenerator idGenerator;

    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    @Transactional
    public Map<String, Object> register(String email, String password, String name) {
        if (userRepo.existsByEmail(email)) {
            throw BusinessException.validation("The user with this email already exists.");
        }

        var user = new UserEntity();
        user.setId(idGenerator.nextId());
        user.setEmail(email);
        user.setPasswordHash(passwordEncoder.encode(password));
        user.setName(name);
        userRepo.save(user);

        var tenant = new TenantEntity();
        tenant.setId(idGenerator.nextId());
        tenant.setName((name != null ? name : email) + "'s Workspace");
        tenant.setSlug("ws-" + user.getId());

        var org = new OrganizationEntity();
        org.setId(idGenerator.nextId());
        org.setTenantId(tenant.getId());
        org.setName("默认部门");
        org.setCode("DEFAULT");

        var orgUser = new OrganizationUserEntity();
        orgUser.setOrgId(org.getId());
        orgUser.setUserId(user.getId());
        orgUser.setTenantId(tenant.getId());

        orgRepo.save(org);
        orgUserRepo.save(orgUser);

        roleRepo.findByCodeAndTenantIdIsNull("owner").ifPresent(ownerRole -> {
            var our = new OrganizationUserRoleEntity();
            our.setOrgId(org.getId());
            our.setUserId(user.getId());
            our.setRoleId(ownerRole.getId());
            our.setTenantId(tenant.getId());
            orgUserRoleRepo.save(our);
        });

        return Map.of("id", user.getId(), "email", email,
                       "tenant_id", tenant.getId(), "org_id", org.getId());
    }

    public Map<String, Object> login(String username, String password) {
        var user = userRepo.findByEmail(username)
                .orElseThrow(() -> BusinessException.validation("Incorrect email or password"));
        if (!verifyPassword(password, user.getPasswordHash())) {
            throw BusinessException.validation("Incorrect email or password");
        }

        var orgUsers = orgUserRepo.findByUserId(user.getId());
        if (orgUsers.isEmpty()) {
            throw BusinessException.validation("User is not a member of any active organization");
        }

        if (orgUsers.size() == 1) {
            return loginToOrg(user, orgUsers.get(0));
        }

        String selectionToken = SaTempUtil.createToken("select:" + user.getId(), 300);
        var orgList = orgUsers.stream().map(ou -> {
            var org = orgRepo.findById(ou.getOrgId()).orElseThrow();
            return Map.<String, Object>of("id", org.getId(), "name", org.getName(),
                                          "tenant_id", org.getTenantId());
        }).toList();

        var result = new HashMap<String, Object>();
        result.put("access_token", null);
        result.put("token_type", "bearer");
        result.put("organizations", orgList);
        result.put("require_org_selection", true);
        result.put("selection_token", selectionToken);
        return result;
    }

    public Map<String, Object> selectOrg(Long orgId, String selectionToken) {
        Object value = SaTempUtil.parseToken(selectionToken);
        if (value == null || !String.valueOf(value).startsWith("select:")) {
            throw BusinessException.validation("Invalid or expired selection token");
        }
        SaTempUtil.deleteToken(selectionToken);
        Long userId = Long.parseLong(String.valueOf(value).substring("select:".length()));
        var ou = orgUserRepo.findByOrgIdAndUserId(orgId, userId)
                .orElseThrow(() -> BusinessException.forbidden("User is not a member of this organization"));
        var user = userRepo.findById(userId).orElseThrow();
        return loginToOrg(user, ou);
    }

    public Map<String, Object> switchOrg(Long userId, Long orgId) {
        StpUtil.logout();
        var ou = orgUserRepo.findByOrgIdAndUserId(orgId, userId)
                .orElseThrow(() -> BusinessException.forbidden("User is not a member of this organization"));
        var user = userRepo.findById(userId).orElseThrow();
        return loginToOrg(user, ou);
    }

    public List<Map<String, Object>> listMyOrgs(Long userId) {
        return orgUserRepo.findByUserId(userId).stream().map(ou -> {
            var org = orgRepo.findById(ou.getOrgId()).orElseThrow();
            return Map.<String, Object>of("id", org.getId(), "name", org.getName(),
                                          "tenant_id", org.getTenantId());
        }).toList();
    }

    public UserReadDto getMe(Long userId, Long orgId, Long tenantId) {
        var user = userRepo.findById(userId).orElseThrow();
        Set<String> perms = getEffectivePermissions(orgId, userId);
        return UserReadDto.builder()
                .id(user.getId()).email(user.getEmail()).name(user.getName())
                .createdAt(user.getCreatedAt()).tenantId(tenantId).orgId(orgId)
                .permissions(new ArrayList<>(perms)).build();
    }

    public List<Map<String, Object>> getMenuTree(Long userId, Long orgId, Long tenantId) {
        Set<String> permCodes = getEffectivePermissions(orgId, userId);
        return menuService.getMenuTree(tenantId, permCodes);
    }

    // ── 私有方法 ──

    private Map<String, Object> loginToOrg(UserEntity user, OrganizationUserEntity ou) {
        var org = orgRepo.findById(ou.getOrgId()).orElseThrow();
        var roleCodes = getRoleCodes(ou.getOrgId(), ou.getUserId());

        StpUtil.login(user.getId(),
                SaLoginConfig
                        .setExtra("tenant_id", org.getTenantId())
                        .setExtra("org_id", org.getId())
                        .setExtra("roles", String.join(",", roleCodes)));

        return Map.of(
                "access_token", StpUtil.getTokenValue(),
                "token_type", "bearer",
                "organization", Map.of("id", org.getId(), "name", org.getName(),
                                       "tenant_id", org.getTenantId()),
                "require_org_selection", false);
    }

    private boolean verifyPassword(String raw, String hash) {
        if (hash == null) return false;
        if (hash.startsWith("$argon2")) return false;
        return passwordEncoder.matches(raw, hash);
    }

    private List<String> getRoleCodes(Long orgId, Long userId) {
        return orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId).stream()
                .map(our -> roleRepo.findById(our.getRoleId()).map(RoleEntity::getCode).orElse(null))
                .filter(Objects::nonNull).toList();
    }

    private Set<String> getEffectivePermissions(Long orgId, Long userId) {
        var roleIds = orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId).stream()
                .map(OrganizationUserRoleEntity::getRoleId).collect(Collectors.toList());
        Set<Long> allRoleIds = new HashSet<>(roleIds);
        Queue<Long> queue = new LinkedList<>(roleIds);
        while (!queue.isEmpty()) {
            Long rid = queue.poll();
            roleRepo.findById(rid).ifPresent(role -> {
                if (role.getParentRoleId() != null && allRoleIds.add(role.getParentRoleId())) {
                    queue.add(role.getParentRoleId());
                }
            });
        }
        if (allRoleIds.isEmpty()) return Set.of();
        return permRepo.findCodesByRoleIds(new ArrayList<>(allRoleIds));
    }
}
```

- [ ] **Step 6: 创建 AuthController**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/controller/AuthController.java
package com.cdm.auth.controller;

import com.cdm.auth.dto.*;
import com.cdm.auth.security.IdentityContext;
import com.cdm.auth.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/register")
    public Map<String, Object> register(@Valid @RequestBody RegisterRequest req) {
        return authService.register(req.getEmail(), req.getPassword(), req.getName());
    }

    @PostMapping("/login/access-token")
    public Map<String, Object> login(@Valid @RequestBody LoginRequest req) {
        return authService.login(req.getUsername(), req.getPassword());
    }

    @PostMapping("/select-org")
    public Map<String, Object> selectOrg(@Valid @RequestBody SelectOrgRequest req) {
        return authService.selectOrg(req.getOrgId(), req.getSelectionToken());
    }

    @PostMapping("/switch-org")
    public Map<String, Object> switchOrg(@Valid @RequestBody SwitchOrgRequest req,
                                         HttpServletRequest httpReq) {
        var ctx = new IdentityContext(httpReq);
        return authService.switchOrg(ctx.getUserId(), req.getOrgId());
    }

    @GetMapping("/my-orgs")
    public List<Map<String, Object>> myOrgs(HttpServletRequest httpReq) {
        var ctx = new IdentityContext(httpReq);
        return authService.listMyOrgs(ctx.getUserId());
    }

    @GetMapping("/me")
    public UserReadDto me(HttpServletRequest httpReq) {
        var ctx = new IdentityContext(httpReq);
        return authService.getMe(ctx.getUserId(), ctx.getOrgId(), ctx.getTenantId());
    }

    @GetMapping("/menu-tree")
    public List<Map<String, Object>> menuTree(HttpServletRequest httpReq) {
        var ctx = new IdentityContext(httpReq);
        return authService.getMenuTree(ctx.getUserId(), ctx.getOrgId(), ctx.getTenantId());
    }
}
```

- [ ] **Step 7: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-java/auth-service/
git commit -m "feat(java): auth-service controller/service/dto/security 业务层"
```

---

## Task 6: 构建与冒烟验证

- [ ] **Step 1: 全量构建（跳过测试）**

```powershell
cd d:\codes\chronic-disease-management\backend-java
mvn clean package -DskipTests
```

Expected: BUILD SUCCESS

- [ ] **Step 2: 启动 auth-service**

```powershell
cd d:\codes\chronic-disease-management\backend-java
$env:JWT_SECRET = "your-jwt-secret-here-must-be-32-chars-long"
java -jar auth-service/target/auth-service-0.1.0.jar
```

Expected: "Started AuthServiceApplication" 监听 8010

- [ ] **Step 3: 启动 Gateway 并验证**

```powershell
cd d:\codes\chronic-disease-management\backend-java
$env:JWT_SECRET = "your-jwt-secret-here-must-be-32-chars-long"
java -jar gateway/target/gateway-0.1.0.jar
```

验证：
```powershell
curl http://localhost:8000/api/v1/auth/login/access-token -Method POST -ContentType "application/json" -Body '{"username":"test@test.com","password":"test"}'
```

Expected: 返回 422，说明 Gateway → auth-service 链路联通

- [ ] **Step 4: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add -A
git commit -m "feat(java): 完成第一期 Gateway + auth-service 构建验证"
```

---

## 自审检查

1. **微服务标准分层**：`controller/` → `service/` → `repository/` → `entity/`，DTO/异常/安全/工具各归其位
2. **设计文档覆盖**：P1-4 全部 API 端点（login、select-org、switch-org、my-orgs、me、menu-tree）
3. **占位符扫描**：无 TBD/TODO
4. **Sa-Token 集成**：Gateway SaReactorFilter + auth-service StpUtil.login(setExtra) + StpInterfaceImpl 权限回调
5. **密码兼容**：Argon2 暂不支持，种子脚本需用 BCrypt 重新生成测试密码
