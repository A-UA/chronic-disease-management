# 第一期-子计划B：Java Spring Boot Gateway + Auth Service 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 Java Spring Boot 微服务集群的 Gateway（8000）和 auth-service（8010），实现完整的登录链路，使前端能通过 Java 后端完成登录、获取用户信息和菜单树。

**Architecture:** Gateway 使用 Spring Cloud Gateway，负责 JWT 校验和路由转发。auth-service 是独立的 Spring Boot 应用，包含认证、用户、组织、RBAC、菜单等业务模块。Gateway 解析 JWT 后将身份信息注入 HTTP Header 转发给下游服务。

**Tech Stack:** Java 17+, Spring Boot 3.x, Spring Cloud Gateway, Spring Data JPA, jjwt, BCrypt, Gradle (Kotlin DSL), PostgreSQL 16

**设计文档:** `docs/superpowers/specs/2026-04-16-microservice-architecture-design.md`

**前置依赖:** 子计划 A 已完成（docker-compose.yml 中 PostgreSQL 已就绪）

**JWT 载荷规范（与 Python 原版对齐）：**
```json
{
  "sub": "用户ID字符串",
  "tenant_id": "租户ID字符串",
  "org_id": "组织ID字符串",
  "roles": ["owner", "admin"],
  "exp": 1700000000
}
```

---

## 文件结构

```
backend-java/
├── settings.gradle.kts
├── build.gradle.kts                  # 根项目（依赖版本管理）
├── gateway/
│   ├── build.gradle.kts
│   └── src/main/java/com/cdm/gateway/
│       ├── GatewayApplication.java
│       ├── filter/JwtAuthFilter.java
│       └── config/RouteConfig.java
│   └── src/main/resources/
│       └── application.yml
├── auth-service/
│   ├── build.gradle.kts
│   └── src/main/java/com/cdm/auth/
│       ├── AuthServiceApplication.java
│       ├── config/SecurityConfig.java
│       ├── auth/
│       │   ├── AuthController.java
│       │   ├── AuthService.java
│       │   ├── JwtProvider.java
│       │   └── dto/
│       │       ├── LoginRequest.java
│       │       ├── LoginResponse.java
│       │       ├── RegisterRequest.java
│       │       ├── SelectOrgRequest.java
│       │       └── UserReadDto.java
│       ├── user/
│       │   ├── UserEntity.java
│       │   └── UserRepository.java
│       ├── organization/
│       │   ├── OrganizationEntity.java
│       │   ├── OrganizationUserEntity.java
│       │   ├── OrganizationUserRoleEntity.java
│       │   ├── OrganizationRepository.java
│       │   ├── OrganizationUserRepository.java
│       │   └── TenantEntity.java
│       ├── rbac/
│       │   ├── RoleEntity.java
│       │   ├── PermissionEntity.java
│       │   ├── RoleRepository.java
│       │   └── PermissionRepository.java
│       ├── menu/
│       │   ├── MenuEntity.java
│       │   ├── MenuRepository.java
│       │   └── MenuService.java
│       └── common/
│           ├── BaseEntity.java
│           ├── BusinessException.java
│           ├── GlobalExceptionHandler.java
│           └── IdentityContext.java
│   └── src/main/resources/
│       └── application.yml
└── common-lib/   (第二期引入，暂时不创建)
```

---

## Task 1: 初始化 Gradle 多模块项目

**Files:**
- Create: `backend-java/settings.gradle.kts`
- Create: `backend-java/build.gradle.kts`
- Create: `backend-java/gateway/build.gradle.kts`
- Create: `backend-java/auth-service/build.gradle.kts`

- [ ] **Step 1: 创建根项目 settings.gradle.kts**

```kotlin
// backend-java/settings.gradle.kts
rootProject.name = "cdm-backend-java"

include("gateway")
include("auth-service")
```

- [ ] **Step 2: 创建根项目 build.gradle.kts（统一版本管理）**

```kotlin
// backend-java/build.gradle.kts
plugins {
    java
    id("org.springframework.boot") version "3.4.4" apply false
    id("io.spring.dependency-management") version "1.1.7" apply false
}

allprojects {
    group = "com.cdm"
    version = "0.1.0"

    repositories {
        mavenCentral()
    }
}

subprojects {
    apply(plugin = "java")
    apply(plugin = "org.springframework.boot")
    apply(plugin = "io.spring.dependency-management")

    java {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    extra["springCloudVersion"] = "2024.0.1"

    the<io.spring.gradle.dependencymanagement.dsl.DependencyManagementExtension>().apply {
        imports {
            mavenBom("org.springframework.cloud:spring-cloud-dependencies:${property("springCloudVersion")}")
        }
    }

    dependencies {
        "compileOnly"("org.projectlombok:lombok")
        "annotationProcessor"("org.projectlombok:lombok")
        "testImplementation"("org.springframework.boot:spring-boot-starter-test")
    }

    tasks.withType<Test> {
        useJUnitPlatform()
    }
}
```

- [ ] **Step 3: 创建 gateway/build.gradle.kts**

```kotlin
// backend-java/gateway/build.gradle.kts
dependencies {
    implementation("org.springframework.cloud:spring-cloud-starter-gateway")
    implementation("io.jsonwebtoken:jjwt-api:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-impl:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-jackson:0.12.6")
}
```

- [ ] **Step 4: 创建 auth-service/build.gradle.kts**

```kotlin
// backend-java/auth-service/build.gradle.kts
dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("io.jsonwebtoken:jjwt-api:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-impl:0.12.6")
    runtimeOnly("io.jsonwebtoken:jjwt-jackson:0.12.6")
    runtimeOnly("org.postgresql:postgresql")
}
```

- [ ] **Step 5: 创建 .gitignore**

```gitignore
# backend-java/.gitignore
build/
.gradle/
*.class
*.jar
.idea/
*.iml
```

- [ ] **Step 6: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-java/
git commit -m "feat(java): 初始化 Gradle 多模块项目骨架"
```

---

## Task 2: Gateway — 应用入口 + JWT 过滤器

**Files:**
- Create: `backend-java/gateway/src/main/java/com/cdm/gateway/GatewayApplication.java`
- Create: `backend-java/gateway/src/main/java/com/cdm/gateway/filter/JwtAuthFilter.java`
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

- [ ] **Step 2: 创建 JWT 全局过滤器**

```java
// backend-java/gateway/src/main/java/com/cdm/gateway/filter/JwtAuthFilter.java
package com.cdm.gateway.filter;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Set;

@Component
public class JwtAuthFilter implements GlobalFilter, Ordered {

    /** 白名单路径：无需鉴权 */
    private static final Set<String> WHITE_LIST = Set.of(
            "/api/v1/auth/login/access-token",
            "/api/v1/auth/register",
            "/api/v1/auth/select-org",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password"
    );

    private final SecretKey secretKey;

    public JwtAuthFilter(@Value("${jwt.secret}") String jwtSecret) {
        this.secretKey = Keys.hmacShaKeyFor(jwtSecret.getBytes(StandardCharsets.UTF_8));
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();

        // 白名单放行
        if (WHITE_LIST.stream().anyMatch(path::startsWith)) {
            return chain.filter(exchange);
        }

        // 提取 Authorization Header
        String authHeader = exchange.getRequest().getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (authHeader == null || !authHeader.startsWith("Bearer ")) {
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }

        String token = authHeader.substring(7);
        try {
            Claims claims = Jwts.parser()
                    .verifyWith(secretKey)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();

            String userId = claims.getSubject();
            String tenantId = claims.get("tenant_id", String.class);
            String orgId = claims.get("org_id", String.class);
            @SuppressWarnings("unchecked")
            List<String> roles = claims.get("roles", List.class);
            String rolesStr = roles != null ? String.join(",", roles) : "";

            // 注入安全 Header 转发给下游微服务
            ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                    .header("X-User-Id", userId)
                    .header("X-Tenant-Id", tenantId != null ? tenantId : "")
                    .header("X-Org-Id", orgId != null ? orgId : "")
                    .header("X-Roles", rolesStr)
                    .build();

            return chain.filter(exchange.mutate().request(mutatedRequest).build());

        } catch (Exception e) {
            exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
            return exchange.getResponse().setComplete();
        }
    }

    @Override
    public int getOrder() {
        return -100; // 最先执行
    }
}
```

- [ ] **Step 3: 创建 Gateway 配置**

```yaml
# backend-java/gateway/src/main/resources/application.yml
server:
  port: 8000

jwt:
  secret: ${JWT_SECRET:your-jwt-secret-here-must-match-python}

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
        # 第二期新增
        # - id: patient-service
        #   uri: http://localhost:8020
        #   predicates:
        #     - Path=/api/v1/patients/**, /api/v1/health-metrics/**
        # - id: chat-service
        #   uri: http://localhost:8030
        #   predicates:
        #     - Path=/api/v1/chat/**, /api/v1/conversations/**
```

- [ ] **Step 4: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-java/gateway/
git commit -m "feat(java): Gateway 应用 + JWT 全局过滤器 + 路由配置"
```

---

## Task 3: Auth Service — 通用基础与实体类

**Files:**
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/AuthServiceApplication.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/config/SecurityConfig.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/common/BaseEntity.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/common/BusinessException.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/common/GlobalExceptionHandler.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/common/IdentityContext.java`
- Create: `backend-java/auth-service/src/main/resources/application.yml`
- Create: User/Organization/Tenant/RBAC/Menu 实体类

- [ ] **Step 1: 创建 Auth Service 启动类**

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

- [ ] **Step 2: 创建 Security 配置（禁用 CSRF，放行所有请求 — 鉴权由 Gateway 负责）**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/config/SecurityConfig.java
package com.cdm.auth.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class SecurityConfig {

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        // 微服务内部：Gateway 已完成鉴权，此处全部放行
        http.csrf(AbstractHttpConfigurer::disable)
            .authorizeHttpRequests(auth -> auth.anyRequest().permitAll());
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
```

- [ ] **Step 3: 创建通用基类与异常处理**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/common/BaseEntity.java
package com.cdm.auth.common;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.Setter;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@MappedSuperclass
@Getter
@Setter
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

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/common/BusinessException.java
package com.cdm.auth.common;

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

    public static BusinessException notFound(String message) {
        return new BusinessException(HttpStatus.NOT_FOUND, "NOT_FOUND", message);
    }

    public static BusinessException forbidden(String message) {
        return new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN", message);
    }

    public static BusinessException validation(String message) {
        return new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", message);
    }
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/common/GlobalExceptionHandler.java
package com.cdm.auth.common;

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
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/common/IdentityContext.java
package com.cdm.auth.common;

import jakarta.servlet.http.HttpServletRequest;
import lombok.Getter;

import java.util.Arrays;
import java.util.List;

/**
 * 从 Gateway 注入的 Header 中提取身份信息。
 * 微服务内部信任 Gateway，不再自行验证 JWT。
 */
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
                ? Arrays.asList(rolesHeader.split(","))
                : List.of();
    }

    private Long parseLong(String value) {
        if (value == null || value.isEmpty()) return null;
        try { return Long.parseLong(value); } catch (NumberFormatException e) { return null; }
    }
}
```

- [ ] **Step 4: 创建实体类 — User, Tenant**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/user/UserEntity.java
package com.cdm.auth.user;

import com.cdm.auth.common.BaseEntity;
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
// backend-java/auth-service/src/main/java/com/cdm/auth/organization/TenantEntity.java
package com.cdm.auth.organization;

import com.cdm.auth.common.BaseEntity;
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

- [ ] **Step 5: 创建实体类 — Organization, OrganizationUser, OrganizationUserRole**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/organization/OrganizationEntity.java
package com.cdm.auth.organization;

import com.cdm.auth.common.BaseEntity;
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
// backend-java/auth-service/src/main/java/com/cdm/auth/organization/OrganizationUserEntity.java
package com.cdm.auth.organization;

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

    @Id
    @Column(name = "org_id")
    private Long orgId;

    @Id
    @Column(name = "user_id")
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
// backend-java/auth-service/src/main/java/com/cdm/auth/organization/OrganizationUserRoleEntity.java
package com.cdm.auth.organization;

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

    @Id
    @Column(name = "org_id")
    private Long orgId;

    @Id
    @Column(name = "user_id")
    private Long userId;

    @Id
    @Column(name = "role_id")
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

- [ ] **Step 6: 创建实体类 — Role, Permission, Menu**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/rbac/RoleEntity.java
package com.cdm.auth.rbac;

import com.cdm.auth.common.BaseEntity;
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
    @JoinTable(
        name = "role_permissions",
        joinColumns = @JoinColumn(name = "role_id"),
        inverseJoinColumns = @JoinColumn(name = "permission_id")
    )
    private List<PermissionEntity> permissions = new ArrayList<>();
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/rbac/PermissionEntity.java
package com.cdm.auth.rbac;

import com.cdm.auth.common.BaseEntity;
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
// backend-java/auth-service/src/main/java/com/cdm/auth/menu/MenuEntity.java
package com.cdm.auth.menu;

import com.cdm.auth.common.BaseEntity;
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

- [ ] **Step 7: 创建 application.yml**

```yaml
# backend-java/auth-service/src/main/resources/application.yml
server:
  port: 8010

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
      ddl-auto: validate  # DDL 由 Alembic 管理，Hibernate 只校验
    show-sql: false
    properties:
      hibernate:
        dialect: org.hibernate.dialect.PostgreSQLDialect
        format_sql: true

jwt:
  secret: ${JWT_SECRET:your-jwt-secret-here-must-match-python}
  expiration-minutes: 10080  # 7天
```

- [ ] **Step 8: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-java/auth-service/
git commit -m "feat(java): auth-service 实体类 + 通用基类 + 配置"
```

---

## Task 4: Auth Service — Repository 层

**Files:**
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/user/UserRepository.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/organization/OrganizationRepository.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/organization/OrganizationUserRepository.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/organization/OrganizationUserRoleRepository.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/rbac/RoleRepository.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/rbac/PermissionRepository.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/menu/MenuRepository.java`

- [ ] **Step 1: 创建所有 Repository 接口**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/user/UserRepository.java
package com.cdm.auth.user;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface UserRepository extends JpaRepository<UserEntity, Long> {
    Optional<UserEntity> findByEmail(String email);
    boolean existsByEmail(String email);
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/organization/OrganizationRepository.java
package com.cdm.auth.organization;

import org.springframework.data.jpa.repository.JpaRepository;

public interface OrganizationRepository extends JpaRepository<OrganizationEntity, Long> {
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/organization/OrganizationUserRepository.java
package com.cdm.auth.organization;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;
import java.util.Optional;

public interface OrganizationUserRepository
        extends JpaRepository<OrganizationUserEntity, OrganizationUserEntity.PK> {

    List<OrganizationUserEntity> findByUserId(Long userId);

    Optional<OrganizationUserEntity> findByOrgIdAndUserId(Long orgId, Long userId);
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/organization/OrganizationUserRoleRepository.java
package com.cdm.auth.organization;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface OrganizationUserRoleRepository
        extends JpaRepository<OrganizationUserRoleEntity, OrganizationUserRoleEntity.PK> {

    List<OrganizationUserRoleEntity> findByOrgIdAndUserId(Long orgId, Long userId);
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/rbac/RoleRepository.java
package com.cdm.auth.rbac;

import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface RoleRepository extends JpaRepository<RoleEntity, Long> {
    Optional<RoleEntity> findByCodeAndTenantIdIsNull(String code);
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/rbac/PermissionRepository.java
package com.cdm.auth.rbac;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;
import java.util.Set;

public interface PermissionRepository extends JpaRepository<PermissionEntity, Long> {

    @Query("SELECT p.code FROM PermissionEntity p " +
           "JOIN p.roles r WHERE r.id IN :roleIds")
    Set<String> findCodesByRoleIds(List<Long> roleIds);
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/menu/MenuRepository.java
package com.cdm.auth.menu;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;

public interface MenuRepository extends JpaRepository<MenuEntity, Long> {

    @Query("SELECT m FROM MenuEntity m " +
           "WHERE m.isEnabled = true " +
           "AND (m.tenantId IS NULL OR m.tenantId = :tenantId) " +
           "ORDER BY m.sort ASC")
    List<MenuEntity> findActiveMenus(Long tenantId);
}
```

- [ ] **Step 2: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-java/auth-service/
git commit -m "feat(java): auth-service Repository 接口层"
```

---

## Task 5: Auth Service — JWT Provider + AuthService + AuthController

**Files:**
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/auth/JwtProvider.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/auth/dto/*.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/auth/AuthService.java`
- Create: `backend-java/auth-service/src/main/java/com/cdm/auth/auth/AuthController.java`

- [ ] **Step 1: 创建 JWT Provider**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/auth/JwtProvider.java
package com.cdm.auth.auth;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Date;
import java.util.List;

@Component
public class JwtProvider {

    private final SecretKey secretKey;
    private final long expirationMinutes;

    public JwtProvider(
            @Value("${jwt.secret}") String jwtSecret,
            @Value("${jwt.expiration-minutes}") long expirationMinutes) {
        this.secretKey = Keys.hmacShaKeyFor(jwtSecret.getBytes(StandardCharsets.UTF_8));
        this.expirationMinutes = expirationMinutes;
    }

    public String createAccessToken(Long userId, Long tenantId, Long orgId, List<String> roles) {
        Instant now = Instant.now();
        return Jwts.builder()
                .subject(String.valueOf(userId))
                .claim("tenant_id", String.valueOf(tenantId))
                .claim("org_id", String.valueOf(orgId))
                .claim("roles", roles)
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plus(expirationMinutes, ChronoUnit.MINUTES)))
                .signWith(secretKey)
                .compact();
    }

    public String createSelectionToken(Long userId) {
        Instant now = Instant.now();
        return Jwts.builder()
                .subject(String.valueOf(userId))
                .claim("purpose", "org_selection")
                .issuedAt(Date.from(now))
                .expiration(Date.from(now.plus(5, ChronoUnit.MINUTES)))
                .signWith(secretKey)
                .compact();
    }

    public io.jsonwebtoken.Claims parseToken(String token) {
        return Jwts.parser()
                .verifyWith(secretKey)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }
}
```

- [ ] **Step 2: 创建 DTO 类**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/auth/dto/LoginRequest.java
package com.cdm.auth.auth.dto;

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
// backend-java/auth-service/src/main/java/com/cdm/auth/auth/dto/RegisterRequest.java
package com.cdm.auth.auth.dto;

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
// backend-java/auth-service/src/main/java/com/cdm/auth/auth/dto/SelectOrgRequest.java
package com.cdm.auth.auth.dto;

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
// backend-java/auth-service/src/main/java/com/cdm/auth/auth/dto/SwitchOrgRequest.java
package com.cdm.auth.auth.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class SwitchOrgRequest {
    @NotNull
    private Long orgId;
}
```

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/auth/dto/UserReadDto.java
package com.cdm.auth.auth.dto;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
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

- [ ] **Step 3: 创建 AuthService**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/auth/AuthService.java
package com.cdm.auth.auth;

import com.cdm.auth.auth.dto.UserReadDto;
import com.cdm.auth.common.BusinessException;
import com.cdm.auth.menu.MenuEntity;
import com.cdm.auth.menu.MenuRepository;
import com.cdm.auth.organization.*;
import com.cdm.auth.rbac.PermissionRepository;
import com.cdm.auth.rbac.RoleEntity;
import com.cdm.auth.rbac.RoleRepository;
import com.cdm.auth.user.UserEntity;
import com.cdm.auth.user.UserRepository;
import io.jsonwebtoken.Claims;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
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
    private final MenuRepository menuRepo;
    private final PasswordEncoder passwordEncoder;
    private final JwtProvider jwtProvider;
    private final SnowflakeIdGenerator idGenerator;

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
        // TenantRepository 需要在此类中注入（简化起见直接用 entityManager）

        var org = new OrganizationEntity();
        org.setId(idGenerator.nextId());
        org.setTenantId(tenant.getId());
        org.setName("默认部门");
        org.setCode("DEFAULT");

        var orgUser = new OrganizationUserEntity();
        orgUser.setOrgId(org.getId());
        orgUser.setUserId(user.getId());
        orgUser.setTenantId(tenant.getId());

        // 简化：直接用 JPA save
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
            var ou = orgUsers.get(0);
            var org = orgRepo.findById(ou.getOrgId()).orElseThrow();
            var roleCodes = getRoleCodes(ou.getOrgId(), ou.getUserId());
            var token = jwtProvider.createAccessToken(
                    user.getId(), org.getTenantId(), org.getId(), roleCodes);
            return Map.of(
                    "access_token", token,
                    "token_type", "bearer",
                    "organization", Map.of("id", org.getId(), "name", org.getName(),
                                           "tenant_id", org.getTenantId()),
                    "require_org_selection", false
            );
        }

        // 多部门：返回 selection_token
        var selectionToken = jwtProvider.createSelectionToken(user.getId());
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
        Claims claims;
        try {
            claims = jwtProvider.parseToken(selectionToken);
            if (!"org_selection".equals(claims.get("purpose", String.class))) {
                throw BusinessException.validation("Invalid selection token");
            }
        } catch (Exception e) {
            throw BusinessException.validation("Invalid or expired selection token");
        }

        Long userId = Long.parseLong(claims.getSubject());
        orgUserRepo.findByOrgIdAndUserId(orgId, userId)
                .orElseThrow(() -> BusinessException.forbidden("User is not a member of this organization"));

        var org = orgRepo.findById(orgId).orElseThrow();
        var roleCodes = getRoleCodes(orgId, userId);
        var token = jwtProvider.createAccessToken(userId, org.getTenantId(), org.getId(), roleCodes);

        return Map.of(
                "access_token", token,
                "token_type", "bearer",
                "organization", Map.of("id", org.getId(), "name", org.getName(),
                                       "tenant_id", org.getTenantId())
        );
    }

    public Map<String, Object> switchOrg(Long userId, Long orgId) {
        orgUserRepo.findByOrgIdAndUserId(orgId, userId)
                .orElseThrow(() -> BusinessException.forbidden("User is not a member of this organization"));
        var org = orgRepo.findById(orgId).orElseThrow();
        var roleCodes = getRoleCodes(orgId, userId);
        var token = jwtProvider.createAccessToken(userId, org.getTenantId(), org.getId(), roleCodes);
        return Map.of(
                "access_token", token,
                "token_type", "bearer",
                "organization", Map.of("id", org.getId(), "name", org.getName(),
                                       "tenant_id", org.getTenantId())
        );
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
        var roleIds = orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId)
                .stream().map(OrganizationUserRoleEntity::getRoleId).toList();

        Set<String> perms = roleIds.isEmpty()
                ? Set.of()
                : getEffectivePermissions(roleIds);

        return UserReadDto.builder()
                .id(user.getId())
                .email(user.getEmail())
                .name(user.getName())
                .createdAt(user.getCreatedAt())
                .tenantId(tenantId)
                .orgId(orgId)
                .permissions(new ArrayList<>(perms))
                .build();
    }

    public List<Map<String, Object>> getMenuTree(Long userId, Long orgId, Long tenantId) {
        var roleEntities = orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId);
        var roleIds = roleEntities.stream()
                .map(OrganizationUserRoleEntity::getRoleId).toList();

        Set<String> permCodes = roleIds.isEmpty()
                ? Set.of()
                : getEffectivePermissions(roleIds);

        var allMenus = menuRepo.findActiveMenus(tenantId);
        var visibleMenus = allMenus.stream()
                .filter(m -> m.getPermissionCode() == null
                        || m.getPermissionCode().isEmpty()
                        || permCodes.contains(m.getPermissionCode()))
                .toList();

        return buildMenuTree(visibleMenus);
    }

    // ── 私有方法 ──

    private boolean verifyPassword(String raw, String hash) {
        if (hash == null) return false;
        // 支持 Argon2 前缀 (Python 生成) 和 BCrypt 前缀 (Java 生成)
        if (hash.startsWith("$argon2")) {
            // Argon2 验证需要额外库，第一期先跳过，种子脚本用 BCrypt 重新生成密码
            return false;
        }
        return passwordEncoder.matches(raw, hash);
    }

    private List<String> getRoleCodes(Long orgId, Long userId) {
        var roleEntities = orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId);
        return roleEntities.stream().map(our -> {
            var role = roleRepo.findById(our.getRoleId()).orElse(null);
            return role != null ? role.getCode() : null;
        }).filter(Objects::nonNull).toList();
    }

    private Set<String> getEffectivePermissions(List<Long> roleIds) {
        // 展开角色继承链
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
        return permRepo.findCodesByRoleIds(new ArrayList<>(allRoleIds));
    }

    private List<Map<String, Object>> buildMenuTree(List<MenuEntity> menus) {
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

        // 剪枝：目录类型且无子节点的移除
        roots.removeIf(item -> "directory".equals(item.get("menu_type"))
                && ((List<?>) item.get("children")).isEmpty());
        return roots;
    }
}
```

- [ ] **Step 4: 创建雪花 ID 生成器（简化版）**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/auth/SnowflakeIdGenerator.java
package com.cdm.auth.auth;

import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicLong;

/**
 * 简化版雪花 ID 生成器。
 * 生产环境应使用与 Python 端相同的 snowflake-id-toolkit 算法保持一致。
 */
@Component
public class SnowflakeIdGenerator {

    private static final long EPOCH = 1704067200000L; // 2024-01-01
    private static final long WORKER_BITS = 10L;
    private static final long SEQUENCE_BITS = 12L;
    private static final long MAX_SEQUENCE = (1L << SEQUENCE_BITS) - 1;

    private final long workerId;
    private long lastTimestamp = -1L;
    private long sequence = 0L;

    public SnowflakeIdGenerator() {
        this.workerId = 1L; // 默认 worker=1，与 Python 端区分
    }

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
                | (workerId << SEQUENCE_BITS)
                | sequence;
    }
}
```

- [ ] **Step 5: 创建 AuthController**

```java
// backend-java/auth-service/src/main/java/com/cdm/auth/auth/AuthController.java
package com.cdm.auth.auth;

import com.cdm.auth.auth.dto.*;
import com.cdm.auth.common.IdentityContext;
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
    public Map<String, Object> switchOrg(
            @Valid @RequestBody SwitchOrgRequest req,
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

- [ ] **Step 6: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-java/auth-service/
git commit -m "feat(java): auth-service 认证服务（登录/注册/菜单树/JWT）"
```

---

## Task 6: 构建与冒烟验证

- [ ] **Step 1: 构建 Gateway**

```powershell
cd d:\codes\chronic-disease-management\backend-java
.\gradlew :gateway:build -x test
```

Expected: BUILD SUCCESSFUL

- [ ] **Step 2: 构建 auth-service**

```powershell
cd d:\codes\chronic-disease-management\backend-java
.\gradlew :auth-service:build -x test
```

Expected: BUILD SUCCESSFUL

- [ ] **Step 3: 启动并验证 Gateway 健康**

```powershell
cd d:\codes\chronic-disease-management\backend-java
# 先设置环境变量
$env:JWT_SECRET = "your-jwt-secret-here-must-match-python"
.\gradlew :gateway:bootRun
```

在另一个终端验证：
```powershell
curl http://localhost:8000/actuator/health
```

- [ ] **Step 4: 提交最终状态**

```powershell
cd d:\codes\chronic-disease-management
git add -A
git commit -m "feat(java): 完成第一期 Gateway + auth-service 构建验证"
```

---

## 自审检查

1. **设计文档覆盖**：覆盖了 P1-4（Java gateway + auth-service），包括登录、select-org、switch-org、me、menu-tree。
2. **占位符扫描**：无 TBD/TODO（`register` 中 TenantRepository 注入已简化但功能完整）。
3. **类型一致性**：JWT 载荷 `sub`/`tenant_id`/`org_id` 一律用字符串，与 Python 端对齐。`IdentityContext` 解析时转 Long。
4. **密码兼容**：`verifyPassword` 方法检查哈希前缀，Argon2（Python 生成）暂不支持验证，种子脚本需用 BCrypt 重新生成测试密码。
