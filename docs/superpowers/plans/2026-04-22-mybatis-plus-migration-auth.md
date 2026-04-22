# cdm-auth MyBatis-Plus Migration Implementation Plan (Part 1: Core & User)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `cdm-common` and `cdm-auth` (User domain) from Spring Data JPA to MyBatis-Plus, changing ID types to `Long`.

**Architecture:** Remove JPA, add MyBatis-Plus. Configure global rules in `application.yml`. Refactor `BaseEntity`, `UserEntity`, create `UserMapper`, and update `AuthService`.

**Tech Stack:** Java 17, Spring Boot 3.5.x, MyBatis-Plus

---

### Task 1: Update Parent & Common Dependencies

**Files:**
- Modify: `backend-java/pom.xml`
- Modify: `backend-java/cdm-common/pom.xml`

- [ ] **Step 1: Add MyBatis-Plus to parent POM**
Modify `backend-java/pom.xml`. Under `<properties>`, add:
```xml
        <mybatis-plus.version>3.5.5</mybatis-plus.version>
```
Under `<dependencyManagement><dependencies>`, add:
```xml
            <dependency>
                <groupId>com.baomidou</groupId>
                <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
                <version>${mybatis-plus.version}</version>
            </dependency>
```

- [ ] **Step 2: Replace JPA with MyBatis-Plus in Common**
Modify `backend-java/cdm-common/pom.xml`. Remove:
```xml
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
```
And add:
```xml
        <dependency>
            <groupId>com.baomidou</groupId>
            <artifactId>mybatis-plus-spring-boot3-starter</artifactId>
        </dependency>
```

- [ ] **Step 3: Verify Maven Load**
Run: `mvn clean -f backend-java/pom.xml`
Expected: BUILD SUCCESS

### Task 2: Refactor BaseEntity

**Files:**
- Modify: `backend-java/cdm-common/src/main/java/com/cdm/common/domain/BaseEntity.java`

- [ ] **Step 1: Update BaseEntity to use Long and remove JPA annotations**
Modify `BaseEntity.java` to:
```java
package com.cdm.common.domain;

import lombok.Getter;
import lombok.Setter;
import java.time.LocalDateTime;

@Getter
@Setter
public abstract class BaseEntity {
    private Long id;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
```

### Task 3: Refactor cdm-auth Configuration

**Files:**
- Modify: `backend-java/cdm-auth/pom.xml`
- Modify: `backend-java/cdm-auth/src/main/resources/application.yml`

- [ ] **Step 1: Clean up cdm-auth POM**
Modify `backend-java/cdm-auth/pom.xml`. Ensure `spring-boot-starter-data-jpa` is NOT present (it shouldn't be, but if it is, remove it). Since it inherits from common, it should be fine. (No code change needed if not present).

- [ ] **Step 2: Update application.yml**
Modify `backend-java/cdm-auth/src/main/resources/application.yml`. Remove the `spring.jpa` block:
```yaml
  jpa:
    hibernate:
      ddl-auto: none
    show-sql: false
    properties:
      hibernate:
        dialect: org.hibernate.dialect.PostgreSQLDialect
        format_sql: true
```
Replace it with MyBatis-Plus config:
```yaml
mybatis-plus:
  global-config:
    db-config:
      id-type: assign_id
      logic-delete-field: is_deleted
      logic-delete-value: 1
      logic-not-delete-value: 0
  configuration:
    log-impl: org.apache.ibatis.logging.stdout.StdOutImpl
```

### Task 4: Refactor UserEntity and Mapper

**Files:**
- Modify: `backend-java/cdm-auth/src/main/java/com/cdm/auth/entity/UserEntity.java`
- Delete: `backend-java/cdm-auth/src/main/java/com/cdm/auth/repository/UserRepository.java`
- Create: `backend-java/cdm-auth/src/main/java/com/cdm/auth/mapper/UserMapper.java`

- [ ] **Step 1: Refactor UserEntity**
Modify `UserEntity.java` to:
```java
package com.cdm.auth.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.cdm.auth.vo.UserVo;
import com.cdm.common.domain.BaseEntity;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@TableName("users")
@Getter @Setter @NoArgsConstructor
public class UserEntity extends BaseEntity {

    private String email;
    private String passwordHash;
    private String name;

    public static UserVo toVo(UserEntity entity) {
        if (entity == null) return null;
        return UserVo.builder()
                .id(entity.getId())
                .email(entity.getEmail())
                .name(entity.getName())
                .build();
    }
}
```
*(Note: `UserVo` must also be updated to use `Long id` in a future task if it's currently `String`. For now, assume `UserVo` is updated alongside).*

- [ ] **Step 2: Delete UserRepository**
Run: `rm backend-java/cdm-auth/src/main/java/com/cdm/auth/repository/UserRepository.java` (Or equivalent powershell `Remove-Item`)

- [ ] **Step 3: Create UserMapper**
Create `UserMapper.java`:
```java
package com.cdm.auth.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.cdm.auth.entity.UserEntity;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserMapper extends BaseMapper<UserEntity> {
}
```

- [ ] **Step 4: Commit**
Run: `git add . && git commit -m "refactor: migrate UserEntity to mybatis-plus"`
