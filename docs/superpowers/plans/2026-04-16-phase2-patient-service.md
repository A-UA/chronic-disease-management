# Patient Service (Phase 2.1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Patient Microservice synchronously across Java and NestJS while expanding JWT parsing to handle soft-RLS security scopes.

**Architecture:** We are augmenting JWT from Auth Services with an `allowed_org_ids` field representing the descending sub-organization tree. Both Java and NestJS Patient Services will expose CRUD endpoints via their Gateways using raw Hibernate/TypeORM filtering over multi-tenant shared tables.

**Tech Stack:** Java 21, Spring Boot 3, Hibernate, NestJS, TypeORM, TCP/HTTP, pgSQL

---

### Task 1: Update Global Identity Models

**Files:**
- Modify: `backend-nestjs/shared/src/interfaces/identity.interface.ts`
- Modify: `backend-java/common-lib/src/main/java/com/cdm/common/security/IdentityPayload.java`

- [ ] **Step 1: Update NestJS interface**

```typescript
// backend-nestjs/shared/src/interfaces/identity.interface.ts
export interface IdentityPayload {
  userId: number;
  tenantId: number;
  orgId: number;
  allowedOrgIds: number[];
  roles: string[];
}
```

- [ ] **Step 2: Update Java class**

```java
// backend-java/common-lib/src/main/java/com/cdm/common/security/IdentityPayload.java
package com.cdm.common.security;
import java.util.List;

public class IdentityPayload {
    private Long userId;
    private Long tenantId;
    private Long orgId;
    private List<Long> allowedOrgIds;
    private List<String> roles;

    // Getters and Setters completely mirroring properties above
    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
    public Long getTenantId() { return tenantId; }
    public void setTenantId(Long tenantId) { this.tenantId = tenantId; }
    public Long getOrgId() { return orgId; }
    public void setOrgId(Long orgId) { this.orgId = orgId; }
    public List<Long> getAllowedOrgIds() { return allowedOrgIds; }
    public void setAllowedOrgIds(List<Long> allowedOrgIds) { this.allowedOrgIds = allowedOrgIds; }
    public List<String> getRoles() { return roles; }
    public void setRoles(List<String> roles) { this.roles = roles; }
}
```

- [ ] **Step 3: Commit**

```bash
git add backend-nestjs/shared backend-java/common-lib
git commit -m "feat(shared): add allowedOrgIds to identity payload"
```

---

### Task 2: Inject allowed_org_ids into NestJS JWT

**Files:**
- Modify: `backend-nestjs/auth-service/src/auth/auth.service.ts`

- [ ] **Step 1: Write descending org tree fetch logic**

Add recursive method to fetch sub-orgs in `auth-service` inside `AuthService` class:
```typescript
  private async getDescendingOrgIds(rootOrgId: number): Promise<number[]> {
    const queue = [rootOrgId];
    const result = new Set<number>();
    
    while (queue.length > 0) {
      const current = queue.shift();
      if (current && !result.has(current)) {
        result.add(current);
        const children = await this.orgRepo.find({ where: { parentId: current } });
        queue.push(...children.map(c => c.id));
      }
    }
    return Array.from(result);
  }
```

- [ ] **Step 2: Inject into token generation**

Modify `login` and `selectOrg` and `switchOrg` where `createAccessToken` is called. Pass `allowedOrgIds` to `JwtProvider`.
Update `src/auth/jwt.provider.ts`:
```typescript
  createAccessToken(userId: number, tenantId: number, orgId: number, allowedOrgIds: number[], roles: string[]) {
    return this.jwtService.sign({
      sub: userId,
      tenant_id: tenantId,
      org_id: orgId,
      allowed_org_ids: allowedOrgIds,
      roles,
    });
  }
```
*Note: Make sure to wire the arguments in auth.service.ts correctly.*

- [ ] **Step 3: Update Gateway guard**

Modify `backend-nestjs/gateway/src/guards/jwt-auth.guard.ts`:
```typescript
      (request as any).identity = {
        userId: Number(payload.sub),
        tenantId: Number(payload.tenant_id),
        orgId: Number(payload.org_id),
        allowedOrgIds: payload.allowed_org_ids || [Number(payload.org_id)],
        roles: payload.roles || [],
      };
```

- [ ] **Step 4: Commit**

```bash
git add backend-nestjs/
git commit -m "feat(nestjs): inject allowed_org_ids into JWT token payload"
```

---

### Task 3: Inject allowed_org_ids into Java JWT

**Files:**
- Modify: `backend-java/auth-service/src/main/java/com/cdm/auth/service/AuthService.java`
- Modify: `backend-java/gateway/src/main/java/com/cdm/gateway/filter/AuthFilter.java`

- [ ] **Step 1: Write recursive Org tree fetch logic in AuthService**

In Java `AuthService`:
```java
    private List<Long> getDescendingOrgIds(Long rootOrgId) {
        List<Long> result = new ArrayList<>();
        java.util.Queue<Long> queue = new java.util.LinkedList<>();
        queue.add(rootOrgId);
        while (!queue.isEmpty()) {
            Long current = queue.poll();
            if (!result.contains(current)) {
                result.add(current);
                List<OrganizationEntity> children = orgRepo.findByParentId(current);
                for (OrganizationEntity child : children) {
                    queue.add(child.getId());
                }
            }
        }
        return result;
    }
```

- [ ] **Step 2: Put it into Sa-Token extra fields**

Modify `StpUtil.login(userId)` code block in `login`, `selectOrg`, `switchOrg` methods:
```java
    List<Long> allowedOrgIds = getDescendingOrgIds(orgId);
    StpUtil.login(user.getId(), new SaLoginModel()
        .setExtra("tenant_id", org.getTenantId())
        .setExtra("org_id", org.getId())
        .setExtra("roles", roleCodes)
        .setExtra("allowed_org_ids", allowedOrgIds));
```

- [ ] **Step 3: Gateway pass header**

Modify `AuthFilter.java` to serialize `allowedOrgIds` into JSON in the custom identity header or pass it comma-separated.
```java
    List<Long> allowedOrgIds = (List<Long>) StpUtil.getExtra("allowed_org_ids");
    // Pass everything as base64 JSON payload
    IdentityPayload identity = new IdentityPayload();
    identity.setUserId(Long.parseLong(userId));
    identity.setTenantId((Long) StpUtil.getExtra("tenant_id"));
    identity.setOrgId((Long) StpUtil.getExtra("org_id"));
    identity.setAllowedOrgIds(allowedOrgIds);
    // Use com.fasterxml.jackson.databind.ObjectMapper to write as string
    String identityJson = new ObjectMapper().writeValueAsString(identity);
    // Encode B64
    String b64Identity = java.util.Base64.getEncoder().encodeToString(identityJson.getBytes());
    
    ServerHttpRequest newReq = exchange.getRequest().mutate()
            .header("X-Identity-Base64", b64Identity)
            .build();
```

- [ ] **Step 4: Commit**

```bash
git add backend-java/
git commit -m "feat(java): inject allowed_org_ids into Sa-Token and encode to gateway header"
```

---

### Task 4: Scaffold Java Patient Service

**Files:**
- Create: `backend-java/patient-service/pom.xml`
- Modify: `backend-java/pom.xml`

- [ ] **Step 1: Create pom.xml**

Create the patient-service pom.xml relying on Spring Boot Web, Data JPA, PostgreSQL, and `common-lib`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>com.cdm</groupId>
        <artifactId>backend-java</artifactId>
        <version>0.1.0</version>
    </parent>
    <artifactId>patient-service</artifactId>
    <dependencies>
        <dependency>
            <groupId>com.cdm</groupId>
            <artifactId>common-lib</artifactId>
            <version>0.1.0</version>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
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
    </dependencies>
</project>
```

- [ ] **Step 2: Add to root pom.xml**

```xml
    <modules>
        <module>common-lib</module>
        <module>gateway</module>
        <module>auth-service</module>
        <module>patient-service</module>
    </modules>
```

- [ ] **Step 3: Setup Application Class & Properties**

Create `backend-java/patient-service/src/main/resources/application.yml`:
```yaml
server:
  port: 8020
spring:
  application:
    name: patient-service
  datasource:
    url: jdbc:postgresql://${DB_HOST:localhost}:${DB_PORT:5432}/${DB_NAME:cdm}
    username: ${DB_USER:postgres}
    password: ${DB_PASS:postgres}
  jpa:
    hibernate:
      ddl-auto: none
    show-sql: true
```

Create `backend-java/patient-service/src/main/java/com/cdm/patient/PatientApplication.java`.

- [ ] **Step 4: Commit**

```bash
git add backend-java/
git commit -m "feat(java): scaffold patient-service module"
```

---

### Task 5: Java Patient Entities

**Files:**
- Create: `backend-java/patient-service/src/main/java/com/cdm/patient/entity/PatientProfileEntity.java`
- Create: `backend-java/patient-service/src/main/java/com/cdm/patient/repository/PatientRepository.java`

- [ ] **Step 1: Write Entity**

```java
package com.cdm.patient.entity;

import jakarta.persistence.*;

@Entity
@Table(name = "patient_profiles")
public class PatientProfileEntity {
    @Id
    private Long id;
    @Column(name = "tenant_id")
    private Long tenantId;
    @Column(name = "org_id")
    private Long orgId;
    private String name;
    private String gender;
    
    // Getters and Setters omitted for brevity in plan, but required in implementation
}
```

- [ ] **Step 2: Write Repository with Explicit RLS filtering**

```java
package com.cdm.patient.repository;

import com.cdm.patient.entity.PatientProfileEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import java.util.List;

public interface PatientRepository extends JpaRepository<PatientProfileEntity, Long> {
    @Query("SELECT p FROM PatientProfileEntity p WHERE p.tenantId = :tenantId AND p.orgId IN :orgIds")
    List<PatientProfileEntity> findAllByContext(@Param("tenantId") Long tenantId, @Param("orgIds") List<Long> orgIds);
}
```

- [ ] **Step 3: Add X-Identity interceptor/resolver**

Create a `HandlerMethodArgumentResolver` to parse `X-Identity-Base64` into `@CurrentUser IdentityPayload user` for the Java Web layer.

- [ ] **Step 4: Commit**

```bash
git add backend-java/patient-service/
git commit -m "feat(java): implement Patient entity and repository with contextual access"
```

---

### Task 6: Scaffold NestJS Patient Service

**Files:**
- Create: `backend-nestjs/patient-service/package.json`
- Modify: `backend-nestjs/pnpm-workspace.yaml`

- [ ] **Step 1: Nest CLI Generation**

Inside `backend-nestjs`:
```bash
nest generate app patient-service
```
Adjust the `main.ts` of the generated app to bind to TCP on `8021` using `@nestjs/microservices`.

```typescript
import { NestFactory } from '@nestjs/core';
import { Transport, MicroserviceOptions } from '@nestjs/microservices';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    AppModule,
    {
      transport: Transport.TCP,
      options: { host: '0.0.0.0', port: 8021 },
    },
  );
  await app.listen();
}
bootstrap();
```

- [ ] **Step 2: Export Patient port constant**

In `@cdm/shared`:
```typescript
export const PATIENT_SERVICE = 'PATIENT_SERVICE';
export const PATIENT_TCP_PORT = 8021;
```

- [ ] **Step 3: Setup TypeORM**

Provide `TypeOrmModule.forRoot` in `patient-service/src/app.module.ts` loading connection config via `process.env`.

- [ ] **Step 4: Commit**

```bash
git add backend-nestjs/
git commit -m "feat(nestjs): scaffold TCP bound patient-service"
```

---

### Task 7: NestJS Patient Flow Context Queries

**Files:**
- Create: `backend-nestjs/patient-service/src/patient/patient.entity.ts`
- Create: `backend-nestjs/patient-service/src/patient/patient.service.ts`

- [ ] **Step 1: Patient Entity**

```typescript
import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('patient_profiles')
export class PatientEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @Column()
  name: string;
}
```

- [ ] **Step 2: Contextual Find Service**

```typescript
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { IdentityPayload } from '@cdm/shared';
import { PatientEntity } from './patient.entity';

@Injectable()
export class PatientService {
  constructor(
    @InjectRepository(PatientEntity)
    private readonly repo: Repository<PatientEntity>,
  ) {}

  async findAll(identity: IdentityPayload) {
    return this.repo.find({
      where: {
        tenantId: identity.tenantId,
        orgId: In(identity.allowedOrgIds),
      },
    });
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add backend-nestjs/patient-service/
git commit -m "feat(nestjs): implement Patient entity and service context querying"
```

---

### Task 8: Update Routing Gateways

**Files:**
- Modify: `backend-java/gateway/src/main/resources/application.yml`
- Modify: `backend-nestjs/gateway/src/app.module.ts`

- [ ] **Step 1: Java Gateway Route**

Append to Spring Cloud Gateway routes:
```yaml
        - id: patient-service
          uri: http://localhost:8020
          predicates:
            - Path=/api/v1/patients/**, /api/v1/health-metrics/**
          filters:
            - AuthFilter
```

- [ ] **Step 2: NestJS Gateway Proxy**

Add ClientProxy for Patient Service and add `PatientProxyController`:
```typescript
    ClientsModule.register([
      { name: AUTH_SERVICE, transport: Transport.TCP, options: { port: AUTH_TCP_PORT } },
      { name: PATIENT_SERVICE, transport: Transport.TCP, options: { port: PATIENT_TCP_PORT } },
    ])
```

Create HTTP endpoints bridging headers (`@CurrentUser`) to TCP Message body options.

- [ ] **Step 3: Connect UI and Finalize**

Run services locally and ensure 0.1.0 baseline is queryable from UI.

```bash
git add .
git commit -m "feat(gateway): route patient service endpoints across both gateways"
```
