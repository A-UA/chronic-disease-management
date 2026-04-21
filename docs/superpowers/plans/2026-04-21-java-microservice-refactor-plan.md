# Java 微服务架构行业标准化整改 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 backend-java 从原型阶段重构为行业标准微服务架构（cdm-* 命名 + Spring Cloud Alibaba 全家桶 + RuoYi 标准身份模式）。

**Architecture:** Maven 多模块聚合（cdm-parent），5 个子模块（cdm-common / cdm-gateway / cdm-auth / cdm-patient / cdm-ai），通过 Nacos 实现服务注册与配置管理，Gateway 负载均衡路由 lb://。

**Tech Stack:** Spring Boot 3.5.13, Spring Cloud 2025.0.1, Spring Cloud Alibaba 2025.0.0.0, Sa-Token 1.40.0, Nacos 2.4.3, OpenFeign, SpringDoc, Micrometer Tracing, PostgreSQL, JPA

---

## Task 1: 项目骨架重构 — 目录重命名与父 POM

**Files:**
- Modify: `backend-java/pom.xml` (父 POM 全量改写)
- Rename: `backend-java/common-lib/` → `backend-java/cdm-common/`
- Rename: `backend-java/gateway/` → `backend-java/cdm-gateway/`
- Rename: `backend-java/auth-service/` → `backend-java/cdm-auth/`
- Rename: `backend-java/patient-service/` → `backend-java/cdm-patient/`
- Create: `backend-java/cdm-ai/` (空模块骨架)

- [ ] **Step 1: 重命名目录**

```powershell
cd d:\codes\chronic-disease-management\backend-java
Rename-Item -Path "common-lib" -NewName "cdm-common"
Rename-Item -Path "gateway" -NewName "cdm-gateway"
Rename-Item -Path "auth-service" -NewName "cdm-auth"
Rename-Item -Path "patient-service" -NewName "cdm-patient"
```

- [ ] **Step 2: 改写父 POM**

将 `backend-java/pom.xml` 完整替换为：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.5.13</version>
        <relativePath/>
    </parent>

    <groupId>com.cdm</groupId>
    <artifactId>cdm-parent</artifactId>
    <version>1.0.0-SNAPSHOT</version>
    <packaging>pom</packaging>
    <name>cdm-parent</name>
    <description>慢病管理微服务聚合工程</description>

    <modules>
        <module>cdm-common</module>
        <module>cdm-gateway</module>
        <module>cdm-auth</module>
        <module>cdm-patient</module>
        <module>cdm-ai</module>
    </modules>

    <properties>
        <java.version>17</java.version>
        <spring-cloud.version>2025.0.1</spring-cloud.version>
        <spring-cloud-alibaba.version>2025.0.0.0</spring-cloud-alibaba.version>
        <sa-token.version>1.40.0</sa-token.version>
        <hutool.version>5.8.35</hutool.version>
        <springdoc.version>2.8.6</springdoc.version>
        <ttl.version>2.14.5</ttl.version>
    </properties>

    <dependencyManagement>
        <dependencies>
            <!-- Spring Cloud BOM -->
            <dependency>
                <groupId>org.springframework.cloud</groupId>
                <artifactId>spring-cloud-dependencies</artifactId>
                <version>${spring-cloud.version}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
            <!-- Spring Cloud Alibaba BOM -->
            <dependency>
                <groupId>com.alibaba.cloud</groupId>
                <artifactId>spring-cloud-alibaba-dependencies</artifactId>
                <version>${spring-cloud-alibaba.version}</version>
                <type>pom</type>
                <scope>import</scope>
            </dependency>
            <!-- 内部模块 -->
            <dependency>
                <groupId>com.cdm</groupId>
                <artifactId>cdm-common</artifactId>
                <version>${project.version}</version>
            </dependency>
            <!-- Sa-Token -->
            <dependency>
                <groupId>cn.dev33</groupId>
                <artifactId>sa-token-spring-boot3-starter</artifactId>
                <version>${sa-token.version}</version>
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
            <!-- Hutool -->
            <dependency>
                <groupId>cn.hutool</groupId>
                <artifactId>hutool-core</artifactId>
                <version>${hutool.version}</version>
            </dependency>
            <!-- TransmittableThreadLocal -->
            <dependency>
                <groupId>com.alibaba</groupId>
                <artifactId>transmittable-thread-local</artifactId>
                <version>${ttl.version}</version>
            </dependency>
        </dependencies>
    </dependencyManagement>

    <build>
        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <configuration>
                    <source>${java.version}</source>
                    <target>${java.version}</target>
                </configuration>
            </plugin>
        </plugins>
    </build>
</project>
```

- [ ] **Step 3: 创建 cdm-ai 空模块骨架**

创建以下目录和文件：
- `backend-java/cdm-ai/pom.xml`
- `backend-java/cdm-ai/src/main/java/com/cdm/ai/AiApplication.java`
- `backend-java/cdm-ai/src/main/resources/application.yml`

cdm-ai/pom.xml:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>com.cdm</groupId>
        <artifactId>cdm-parent</artifactId>
        <version>1.0.0-SNAPSHOT</version>
    </parent>

    <artifactId>cdm-ai</artifactId>
    <name>cdm-ai</name>
    <description>AI 微服务 - 知识库/文档/会话管理</description>

    <dependencies>
        <dependency>
            <groupId>com.cdm</groupId>
            <artifactId>cdm-common</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>org.postgresql</groupId>
            <artifactId>postgresql</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>com.alibaba.cloud</groupId>
            <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
        </dependency>
        <dependency>
            <groupId>com.alibaba.cloud</groupId>
            <artifactId>spring-cloud-starter-alibaba-nacos-config</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-starter-openfeign</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-starter-loadbalancer</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-actuator</artifactId>
        </dependency>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
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

AiApplication.java:
```java
package com.cdm.ai;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;

@SpringBootApplication
@EnableDiscoveryClient
@EnableFeignClients
public class AiApplication {
    public static void main(String[] args) {
        SpringApplication.run(AiApplication.class, args);
    }
}
```

- [ ] **Step 4: 更新各子模块 POM 的 parent 引用**

所有子模块的 `pom.xml` 中的 `<parent>` 部分需要更新：
- groupId: `com.cdm`
- artifactId: `cdm-parent`
- version: `1.0.0-SNAPSHOT`

同时更新各子模块自己的 artifactId：
- cdm-common: `<artifactId>cdm-common</artifactId>`
- cdm-gateway: `<artifactId>cdm-gateway</artifactId>`
- cdm-auth: `<artifactId>cdm-auth</artifactId>`
- cdm-patient: `<artifactId>cdm-patient</artifactId>`

需要逐个打开并修改。

- [ ] **Step 5: 验证 Maven 编译**

```powershell
cd d:\codes\chronic-disease-management\backend-java
mvn clean compile -pl cdm-common
```

Expected: BUILD SUCCESS（cdm-common 编译通过即可，其他模块后续 Task 修改后再验证）

- [ ] **Step 6: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add -A
git commit -m "refactor: 重命名模块为 cdm-* 前缀，升级至 Spring Boot 3.5 + Spring Cloud Alibaba 2025.0"
```

---

## Task 2: cdm-common — Result/ResultCode/BusinessException

**Files:**
- Create: `cdm-common/src/main/java/com/cdm/common/domain/Result.java`
- Create: `cdm-common/src/main/java/com/cdm/common/domain/ResultCode.java`
- Create: `cdm-common/src/main/java/com/cdm/common/exception/BusinessException.java`
- Create: `cdm-common/src/main/java/com/cdm/common/exception/GlobalExceptionHandler.java`
- Modify: `cdm-common/pom.xml` (确保 validation 依赖)

- [ ] **Step 1: 创建 ResultCode 枚举**

```java
package com.cdm.common.domain;

import lombok.Getter;
import lombok.RequiredArgsConstructor;

@Getter
@RequiredArgsConstructor
public enum ResultCode {
    SUCCESS(200, "操作成功"),
    BAD_REQUEST(400, "请求参数错误"),
    UNAUTHORIZED(401, "未登录或令牌已过期"),
    FORBIDDEN(403, "无此权限"),
    NOT_FOUND(404, "资源不存在"),
    VALIDATION_ERROR(422, "参数校验失败"),
    INTERNAL_ERROR(500, "服务器内部错误");

    private final int code;
    private final String message;
}
```

- [ ] **Step 2: 创建 Result<T>**

```java
package com.cdm.common.domain;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Data;

@Data
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Result<T> {
    private int code;
    private String message;
    private T data;

    private Result() {}

    public static <T> Result<T> ok(T data) {
        Result<T> r = new Result<>();
        r.code = ResultCode.SUCCESS.getCode();
        r.message = ResultCode.SUCCESS.getMessage();
        r.data = data;
        return r;
    }

    public static <T> Result<T> ok() {
        return ok(null);
    }

    public static <T> Result<T> fail(ResultCode code) {
        Result<T> r = new Result<>();
        r.code = code.getCode();
        r.message = code.getMessage();
        return r;
    }

    public static <T> Result<T> fail(ResultCode code, String message) {
        Result<T> r = new Result<>();
        r.code = code.getCode();
        r.message = message;
        return r;
    }

    public static <T> Result<T> fail(int code, String message) {
        Result<T> r = new Result<>();
        r.code = code;
        r.message = message;
        return r;
    }
}
```

- [ ] **Step 3: 创建 BusinessException**

```java
package com.cdm.common.exception;

import com.cdm.common.domain.ResultCode;
import lombok.Getter;

@Getter
public class BusinessException extends RuntimeException {
    private final ResultCode resultCode;

    public BusinessException(ResultCode resultCode) {
        super(resultCode.getMessage());
        this.resultCode = resultCode;
    }

    public BusinessException(ResultCode resultCode, String message) {
        super(message);
        this.resultCode = resultCode;
    }

    public static BusinessException notFound(String message) {
        return new BusinessException(ResultCode.NOT_FOUND, message);
    }

    public static BusinessException forbidden(String message) {
        return new BusinessException(ResultCode.FORBIDDEN, message);
    }

    public static BusinessException forbidden() {
        return new BusinessException(ResultCode.FORBIDDEN);
    }

    public static BusinessException validation(String message) {
        return new BusinessException(ResultCode.VALIDATION_ERROR, message);
    }

    public static BusinessException badRequest(String message) {
        return new BusinessException(ResultCode.BAD_REQUEST, message);
    }

    public static BusinessException unauthorized(String message) {
        return new BusinessException(ResultCode.UNAUTHORIZED, message);
    }

    public static BusinessException internal(String message) {
        return new BusinessException(ResultCode.INTERNAL_ERROR, message);
    }
}
```

- [ ] **Step 4: 创建 GlobalExceptionHandler**

```java
package com.cdm.common.exception;

import com.cdm.common.domain.Result;
import com.cdm.common.domain.ResultCode;
import jakarta.validation.ConstraintViolation;
import jakarta.validation.ConstraintViolationException;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.resource.NoResourceFoundException;

import java.util.stream.Collectors;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(BusinessException.class)
    public Result<Void> handleBusiness(BusinessException e) {
        log.warn("业务异常: code={}, msg={}", e.getResultCode().getCode(), e.getMessage());
        return Result.fail(e.getResultCode(), e.getMessage());
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<Void> handleValidation(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .map(FieldError::getDefaultMessage)
                .collect(Collectors.joining("; "));
        return Result.fail(ResultCode.VALIDATION_ERROR, msg);
    }

    @ExceptionHandler(ConstraintViolationException.class)
    public Result<Void> handleConstraint(ConstraintViolationException e) {
        String msg = e.getConstraintViolations().stream()
                .map(ConstraintViolation::getMessage)
                .collect(Collectors.joining("; "));
        return Result.fail(ResultCode.VALIDATION_ERROR, msg);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public Result<Void> handleNotReadable(HttpMessageNotReadableException e) {
        return Result.fail(ResultCode.BAD_REQUEST, "请求体格式错误");
    }

    @ExceptionHandler(MissingServletRequestParameterException.class)
    public Result<Void> handleMissingParam(MissingServletRequestParameterException e) {
        return Result.fail(ResultCode.BAD_REQUEST, "缺少必要参数: " + e.getParameterName());
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public Result<Void> handleMethodNotSupported(HttpRequestMethodNotSupportedException e) {
        return Result.fail(ResultCode.BAD_REQUEST, "不支持的请求方法: " + e.getMethod());
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public Result<Void> handleNoResource(NoResourceFoundException e) {
        return Result.fail(ResultCode.NOT_FOUND, "资源不存在");
    }

    @ExceptionHandler(Exception.class)
    public Result<Void> handleUnknown(Exception e) {
        log.error("未知异常", e);
        return Result.fail(ResultCode.INTERNAL_ERROR, "服务器内部错误");
    }
}
```

- [ ] **Step 5: 验证编译**

```powershell
cd d:\codes\chronic-disease-management\backend-java
mvn clean compile -pl cdm-common
```

Expected: BUILD SUCCESS

- [ ] **Step 6: 提交**

```powershell
git add -A ; git commit -m "feat(common): 添加 Result<T> 统一响应体 + BusinessException 异常框架 + GlobalExceptionHandler"
```

---

## Task 3: cdm-common — 三层身份模式 + BaseEntity + SnowflakeId

**Files:**
- Create: `cdm-common/src/main/java/com/cdm/common/security/SecurityContextHolder.java`
- Create: `cdm-common/src/main/java/com/cdm/common/security/SecurityUtils.java`
- Create: `cdm-common/src/main/java/com/cdm/common/security/HeaderInterceptor.java`
- Create: `cdm-common/src/main/java/com/cdm/common/feign/FeignRequestInterceptor.java`
- Create: `cdm-common/src/main/java/com/cdm/common/config/WebMvcAutoConfiguration.java`
- Create: `cdm-common/src/main/java/com/cdm/common/domain/BaseEntity.java`
- Modify: `cdm-common/src/main/java/com/cdm/common/util/SnowflakeIdGenerator.java` (下沉统一)
- Create: `cdm-common/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`

- [ ] **Step 1: 创建 SecurityContextHolder**

```java
package com.cdm.common.security;

import com.alibaba.ttl.TransmittableThreadLocal;
import java.util.HashMap;
import java.util.Map;

public class SecurityContextHolder {
    private static final TransmittableThreadLocal<Map<String, Object>> CONTEXT =
            new TransmittableThreadLocal<>() {
                @Override
                protected Map<String, Object> initialValue() {
                    return new HashMap<>();
                }
            };

    public static void set(String key, Object value) {
        CONTEXT.get().put(key, value);
    }

    @SuppressWarnings("unchecked")
    public static <T> T get(String key) {
        return (T) CONTEXT.get().get(key);
    }

    public static String getString(String key) {
        Object val = CONTEXT.get().get(key);
        return val == null ? null : val.toString();
    }

    public static void remove() {
        CONTEXT.remove();
    }
}
```

- [ ] **Step 2: 创建 SecurityUtils**

```java
package com.cdm.common.security;

import com.cdm.common.exception.BusinessException;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class SecurityUtils {
    public static final String USER_ID = "userId";
    public static final String TENANT_ID = "tenantId";
    public static final String ORG_ID = "orgId";
    public static final String ROLES = "roles";
    public static final String ALLOWED_ORG_IDS = "allowedOrgIds";

    public static String getUserId() {
        String userId = SecurityContextHolder.getString(USER_ID);
        if (userId == null || userId.isBlank()) {
            throw BusinessException.unauthorized("无法获取用户身份");
        }
        return userId;
    }

    public static String getTenantId() {
        return SecurityContextHolder.getString(TENANT_ID);
    }

    public static String getOrgId() {
        return SecurityContextHolder.getString(ORG_ID);
    }

    public static List<String> getRoles() {
        String roles = SecurityContextHolder.getString(ROLES);
        if (roles == null || roles.isBlank()) return Collections.emptyList();
        return Arrays.asList(roles.split(","));
    }

    public static List<String> getAllowedOrgIds() {
        String ids = SecurityContextHolder.getString(ALLOWED_ORG_IDS);
        if (ids == null || ids.isBlank()) return Collections.emptyList();
        return Arrays.asList(ids.split(","));
    }
}
```

- [ ] **Step 3: 创建 HeaderInterceptor**

```java
package com.cdm.common.security;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.servlet.AsyncHandlerInterceptor;

public class HeaderInterceptor implements AsyncHandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        SecurityContextHolder.set(SecurityUtils.USER_ID, request.getHeader("X-User-Id"));
        SecurityContextHolder.set(SecurityUtils.TENANT_ID, request.getHeader("X-Tenant-Id"));
        SecurityContextHolder.set(SecurityUtils.ORG_ID, request.getHeader("X-Org-Id"));
        SecurityContextHolder.set(SecurityUtils.ROLES, request.getHeader("X-Roles"));
        SecurityContextHolder.set(SecurityUtils.ALLOWED_ORG_IDS, request.getHeader("X-Allowed-Org-Ids"));
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        SecurityContextHolder.remove();
    }
}
```

- [ ] **Step 4: 创建 FeignRequestInterceptor**

```java
package com.cdm.common.feign;

import com.cdm.common.security.SecurityContextHolder;
import com.cdm.common.security.SecurityUtils;
import feign.RequestInterceptor;
import feign.RequestTemplate;

public class FeignRequestInterceptor implements RequestInterceptor {
    @Override
    public void apply(RequestTemplate template) {
        addHeader(template, "X-User-Id", SecurityUtils.USER_ID);
        addHeader(template, "X-Tenant-Id", SecurityUtils.TENANT_ID);
        addHeader(template, "X-Org-Id", SecurityUtils.ORG_ID);
        addHeader(template, "X-Roles", SecurityUtils.ROLES);
        addHeader(template, "X-Allowed-Org-Ids", SecurityUtils.ALLOWED_ORG_IDS);
    }

    private void addHeader(RequestTemplate template, String headerName, String contextKey) {
        String value = SecurityContextHolder.getString(contextKey);
        if (value != null && !value.isBlank()) {
            template.header(headerName, value);
        }
    }
}
```

- [ ] **Step 5: 创建 WebMvcAutoConfiguration**

```java
package com.cdm.common.config;

import com.cdm.common.feign.FeignRequestInterceptor;
import com.cdm.common.security.HeaderInterceptor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

@Configuration
public class WebMvcAutoConfiguration implements WebMvcConfigurer {
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new HeaderInterceptor())
                .addPathPatterns("/api/**");
    }

    @Bean
    public FeignRequestInterceptor feignRequestInterceptor() {
        return new FeignRequestInterceptor();
    }
}
```

- [ ] **Step 6: 创建 BaseEntity**

```java
package com.cdm.common.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Id;
import jakarta.persistence.MappedSuperclass;
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
    private String id;

    @CreationTimestamp
    @Column(name = "created_at", updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;
}
```

- [ ] **Step 7: 统一 SnowflakeIdGenerator（确认已存在或创建）**

确保 `cdm-common/src/main/java/com/cdm/common/util/SnowflakeIdGenerator.java` 内容为：

```java
package com.cdm.common.util;

import cn.hutool.core.lang.Snowflake;
import cn.hutool.core.util.IdUtil;
import org.springframework.stereotype.Component;

@Component
public class SnowflakeIdGenerator {
    private static final Snowflake SNOWFLAKE = IdUtil.getSnowflake(1, 1);

    public String nextId() {
        return String.valueOf(SNOWFLAKE.nextId());
    }

    public static String generateId() {
        return String.valueOf(SNOWFLAKE.nextId());
    }
}
```

- [ ] **Step 8: 创建自动装配注册文件**

文件路径: `cdm-common/src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`

```
com.cdm.common.config.JacksonAutoConfiguration
com.cdm.common.config.WebMvcAutoConfiguration
com.cdm.common.exception.GlobalExceptionHandler
```

- [ ] **Step 9: 更新 cdm-common pom.xml 依赖**

确保包含以下依赖：
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-validation</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-jpa</artifactId>
</dependency>
<dependency>
    <groupId>cn.hutool</groupId>
    <artifactId>hutool-core</artifactId>
</dependency>
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>transmittable-thread-local</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-openfeign</artifactId>
</dependency>
<dependency>
    <groupId>org.projectlombok</groupId>
    <artifactId>lombok</artifactId>
    <optional>true</optional>
</dependency>
```

- [ ] **Step 10: 验证编译**

```powershell
cd d:\codes\chronic-disease-management\backend-java
mvn clean compile -pl cdm-common
```

Expected: BUILD SUCCESS

- [ ] **Step 11: 提交**

```powershell
git add -A ; git commit -m "feat(common): 添加三层身份模式 SecurityContextHolder/SecurityUtils/HeaderInterceptor + BaseEntity + FeignInterceptor"
```

---

## Task 4: cdm-gateway — 重构鉴权 + 异常处理 + Nacos 路由

**Files:**
- Modify: `cdm-gateway/pom.xml` (添加 Nacos/LoadBalancer 依赖)
- Create: `cdm-gateway/src/main/java/com/cdm/gateway/config/IgnoreWhiteProperties.java`
- Modify: `cdm-gateway/src/main/java/com/cdm/gateway/config/SaTokenConfig.java` (重构为 AuthFilter)
- Create: `cdm-gateway/src/main/java/com/cdm/gateway/filter/AuthFilter.java`
- Create: `cdm-gateway/src/main/java/com/cdm/gateway/handler/GatewayExceptionHandler.java`
- Modify: `cdm-gateway/src/main/resources/application.yml` (端口 8001 + lb:// 路由)
- Create: `cdm-gateway/src/main/resources/bootstrap.yml`

此 Task 文件较多，具体实现代码参考设计规格文档 Section 5。核心步骤：

- [ ] **Step 1: 更新 cdm-gateway pom.xml**

添加 Nacos Discovery、LoadBalancer、SpringDoc WebFlux 依赖。移除不需要的依赖。

- [ ] **Step 2: 创建 IgnoreWhiteProperties**

白名单从 yaml 配置读取。

- [ ] **Step 3: 创建 AuthFilter（替代原 SaTokenConfig 中的内联 GlobalFilter）**

按设计规格中的 RuoYi 标准模式：白名单 → 鉴权 → 安全清洗 → Header 注入。

- [ ] **Step 4: 创建 GatewayExceptionHandler**

实现 ErrorWebExceptionHandler，统一 JSON 响应。

- [ ] **Step 5: 重写 application.yml**

端口改为 8001，路由使用 lb:// 模式。

- [ ] **Step 6: 创建 bootstrap.yml**

Nacos 连接配置。

- [ ] **Step 7: 删除旧的 SaTokenConfig 中的过滤器逻辑（保留 StpLogic Bean）**

- [ ] **Step 8: 验证编译**

```powershell
mvn clean compile -pl cdm-gateway
```

- [ ] **Step 9: 提交**

```powershell
git add -A ; git commit -m "feat(gateway): 重构为 RuoYi 标准 AuthFilter + GatewayExceptionHandler + Nacos lb:// 路由"
```

---

## Task 5: cdm-auth — VO/DTO 分层 + SecurityUtils + Nacos

**Files:**
- Create: `cdm-auth/src/main/java/com/cdm/auth/dto/LoginDto.java`
- Create: `cdm-auth/src/main/java/com/cdm/auth/dto/RegisterDto.java`
- Create: `cdm-auth/src/main/java/com/cdm/auth/dto/SelectOrgDto.java`
- Create: `cdm-auth/src/main/java/com/cdm/auth/vo/LoginVo.java`
- Create: `cdm-auth/src/main/java/com/cdm/auth/vo/UserVo.java`
- Create: `cdm-auth/src/main/java/com/cdm/auth/vo/MenuVo.java`
- Create: `cdm-auth/src/main/java/com/cdm/auth/vo/OrganizationVo.java`
- Modify: `cdm-auth/src/main/java/com/cdm/auth/controller/*.java` (返回 Result<VO>)
- Modify: `cdm-auth/src/main/java/com/cdm/auth/service/AuthService.java` (返回 VO)
- Delete: `cdm-auth/src/main/java/com/cdm/auth/exception/GlobalExceptionHandler.java` (已下沉 common)
- Delete: `cdm-auth/src/main/java/com/cdm/auth/exception/BusinessException.java` (已下沉 common)
- Modify: `cdm-auth/pom.xml` (添加 Nacos 依赖)
- Create: `cdm-auth/src/main/resources/bootstrap.yml`

核心步骤：

- [ ] **Step 1: 创建 DTO 类**（LoginDto, RegisterDto, SelectOrgDto）带 @Valid 注解

- [ ] **Step 2: 创建 VO 类**（LoginVo, UserVo, MenuVo, OrganizationVo）

- [ ] **Step 3: Entity 类添加 static toVo() 工厂方法**

- [ ] **Step 4: 重构 Service 层**
- 接收 SecurityUtils 而非散装参数
- 返回 VO 而非 Map/Entity

- [ ] **Step 5: 重构 Controller 层**
- 返回 `Result<XxxVo>`
- 添加 `@Tag` / `@Operation` 注解

- [ ] **Step 6: 删除 auth 内部的 GlobalExceptionHandler 和 BusinessException**（已由 cdm-common 自动装配提供）

- [ ] **Step 7: 删除冗余的 SnowflakeIdGenerator**（使用 cdm-common 的）

- [ ] **Step 8: 更新 pom.xml 添加 Nacos + SpringDoc 依赖**

- [ ] **Step 9: 创建 bootstrap.yml**

- [ ] **Step 10: 修改 application.yml 端口为 8011**

- [ ] **Step 11: 验证编译**

```powershell
mvn clean compile -pl cdm-common,cdm-auth
```

- [ ] **Step 12: 提交**

```powershell
git add -A ; git commit -m "feat(auth): VO/DTO 分层 + SecurityUtils 身份获取 + Nacos 接入"
```

---

## Task 6: cdm-patient — 精简域 + DTO/VO + SecurityUtils

**Files:**
- Delete: `cdm-patient/.../controller/KnowledgeBaseController.java` (迁移到 cdm-ai)
- Delete: `cdm-patient/.../controller/DocumentController.java` (迁移到 cdm-ai)
- Delete: `cdm-patient/.../entity/KnowledgeBaseEntity.java` (迁移到 cdm-ai)
- Delete: `cdm-patient/.../entity/DocumentEntity.java` (迁移到 cdm-ai)
- Delete: `cdm-patient/.../repository/KnowledgeBaseRepository.java` (迁移到 cdm-ai)
- Delete: `cdm-patient/.../repository/DocumentRepository.java` (迁移到 cdm-ai)
- Delete: `cdm-patient/.../client/AgentClient.java` (迁移到 cdm-ai)
- Delete: `cdm-patient/.../service/MinioService.java` (迁移到 cdm-ai)
- Create: `cdm-patient/.../dto/CreatePatientDto.java`
- Create: `cdm-patient/.../vo/PatientVo.java`（及其他 VO）
- Modify: `cdm-patient/.../controller/PatientController.java` (等全部 Controller)
- Modify: `cdm-patient/pom.xml`
- Create: `cdm-patient/src/main/resources/bootstrap.yml`

核心步骤：

- [ ] **Step 1: 从 patient 中删除 AI 域代码**

将 KnowledgeBase、Document、AgentClient、MinioService 相关文件从 cdm-patient 删除（代码在 Task 7 中迁移到 cdm-ai）。

- [ ] **Step 2: 创建 DTO/VO 类**

- [ ] **Step 3: 重构 Controller**
- 移除 `@RequestHeader("X-Identity-Base64")` → `SecurityUtils`
- 返回 `Result<PatientVo>`

- [ ] **Step 4: 重构 Service**
- `RuntimeException` → `BusinessException`

- [ ] **Step 5: Entity 继承 BaseEntity，使用 Lombok**

- [ ] **Step 6: 更新 pom.xml，添加 Nacos + validation**

- [ ] **Step 7: 创建 bootstrap.yml，端口改为 8021**

- [ ] **Step 8: 验证编译**

```powershell
mvn clean compile -pl cdm-common,cdm-patient
```

- [ ] **Step 9: 提交**

```powershell
git add -A ; git commit -m "feat(patient): 剥离 AI 域 + DTO/VO 分层 + SecurityUtils + Nacos"
```

---

## Task 7: cdm-ai — 迁入知识库/文档代码 + OpenFeign

**Files:**
- Create: `cdm-ai/src/main/java/com/cdm/ai/entity/KnowledgeBaseEntity.java` (从 patient 迁入改造)
- Create: `cdm-ai/src/main/java/com/cdm/ai/entity/DocumentEntity.java` (从 patient 迁入改造)
- Create: `cdm-ai/src/main/java/com/cdm/ai/repository/*.java`
- Create: `cdm-ai/src/main/java/com/cdm/ai/controller/KnowledgeBaseController.java`
- Create: `cdm-ai/src/main/java/com/cdm/ai/controller/DocumentController.java`
- Create: `cdm-ai/src/main/java/com/cdm/ai/service/KnowledgeBaseService.java`
- Create: `cdm-ai/src/main/java/com/cdm/ai/service/DocumentService.java`
- Create: `cdm-ai/src/main/java/com/cdm/ai/service/MinioService.java`
- Create: `cdm-ai/src/main/java/com/cdm/ai/client/AgentClient.java` (OpenFeign 声明式)
- Create: `cdm-ai/src/main/java/com/cdm/ai/dto/*.java`
- Create: `cdm-ai/src/main/java/com/cdm/ai/vo/*.java`
- Create: `cdm-ai/src/main/resources/bootstrap.yml`

核心步骤：

- [ ] **Step 1: 迁入 Entity 类**，改用 Lombok + BaseEntity

- [ ] **Step 2: 创建 Repository 接口**

- [ ] **Step 3: 创建 DTO/VO 类**

- [ ] **Step 4: 创建 AgentClient OpenFeign 接口**

```java
@FeignClient(name = "agent-client", url = "${agent.url:http://localhost:8000}")
public interface AgentClient {
    @PostMapping(value = "/internal/knowledge/parse", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    AgentParseResponse parseDocument(@RequestPart("file") MultipartFile file, @RequestPart("kb_id") String kbId);

    @DeleteMapping("/internal/knowledge/vectors/kb/{kbId}")
    void deleteKbVectors(@PathVariable String kbId);

    @DeleteMapping("/internal/knowledge/vectors/kb/{kbId}/doc/{filename}")
    void deleteDocVectors(@PathVariable String kbId, @PathVariable String filename);
}
```

- [ ] **Step 5: 创建 MinioService**

- [ ] **Step 6: 创建 KnowledgeBaseService（含全生命周期编排）**

- [ ] **Step 7: 创建 Controller 层**，返回 `Result<XxxVo>`，用 SecurityUtils 替代硬编码 tenantId

- [ ] **Step 8: 配置 bootstrap.yml + application.yml，端口 8031**

- [ ] **Step 9: 验证编译**

```powershell
mvn clean compile -pl cdm-common,cdm-ai
```

- [ ] **Step 10: 提交**

```powershell
git add -A ; git commit -m "feat(ai): 新建 AI 微服务，迁入知识库/文档管理 + OpenFeign Agent 调用"
```

---

## Task 8: Nacos 基础设施 + Docker Compose

**Files:**
- Modify: `docker-compose.yml` (添加 Nacos 容器)
- Create: Nacos 共享配置 `cdm-common.yml` 模板

- [ ] **Step 1: 更新 docker-compose.yml 添加 Nacos**

```yaml
nacos:
  image: nacos/nacos-server:v2.4.3
  container_name: cdm-nacos
  environment:
    - MODE=standalone
    - NACOS_AUTH_ENABLE=false
  ports:
    - "8848:8848"
    - "9848:9848"
  restart: unless-stopped
```

- [ ] **Step 2: 创建 Nacos 配置模板文档**

在 `docs/nacos/` 下创建各 Data ID 的 yml 模板供初始化导入。

- [ ] **Step 3: 提交**

```powershell
git add -A ; git commit -m "infra: Docker Compose 添加 Nacos + 配置模板"
```

---

## Task 9: 跨切面 — SpringDoc + Actuator + Tracing

**Files:**
- 各微服务 Controller 添加 `@Tag` / `@Operation` 注解（已在 Task 5-7 中部分完成）
- 各微服务 pom.xml 确保包含 actuator + tracing 依赖
- 各微服务创建 logback-spring.xml（含 traceId 格式）

- [ ] **Step 1: 各微服务确认 SpringDoc 依赖已就位**

- [ ] **Step 2: 创建统一 logback-spring.xml 模板**

```xml
<configuration>
    <appender name="CONSOLE" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
            <pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} [%thread] [%X{traceId:-}] %-5level %logger{36} - %msg%n</pattern>
        </encoder>
    </appender>
    <root level="INFO">
        <appender-ref ref="CONSOLE"/>
    </root>
</configuration>
```

- [ ] **Step 3: 验证全量编译**

```powershell
cd d:\codes\chronic-disease-management\backend-java
mvn clean compile
```

Expected: BUILD SUCCESS（所有模块）

- [ ] **Step 4: 提交**

```powershell
git add -A ; git commit -m "feat: 添加 SpringDoc 接口文档 + 日志链路追踪格式 + Actuator 健康检查"
```

---

## Task 10: 更新 AGENTS.md + 最终验证

**Files:**
- Modify: `AGENTS.md` (更新 Java 微服务部分)

- [ ] **Step 1: 更新 AGENTS.md 中的 Java 部分**

更新端口表、技术栈版本、启动命令、目录结构说明。

- [ ] **Step 2: 全量编译验证**

```powershell
cd d:\codes\chronic-disease-management\backend-java
mvn clean package -DskipTests
```

Expected: BUILD SUCCESS for all 5 modules

- [ ] **Step 3: 最终提交**

```powershell
git add -A ; git commit -m "docs: 更新 AGENTS.md Java 微服务架构说明"
```
