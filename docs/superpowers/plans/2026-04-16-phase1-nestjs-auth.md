# 第一期-子计划C：NestJS Gateway + Auth Service 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 NestJS 微服务集群的 Gateway（8001）和 auth-service（8011 TCP），实现与 Java 版完全对等的登录链路，使前端通过 `VITE_BACKEND=nestjs` 环境变量切换后也能完成登录。

**Architecture:** Gateway 是标准 NestJS HTTP 应用，接收前端请求后通过 TCP ClientProxy 转发给 auth-service 微服务。Gateway 负责 JWT 校验（Guard），auth-service 使用 `@MessagePattern` 处理 TCP 消息。采用 pnpm workspace monorepo 管理。

**Tech Stack:** NestJS 10.x, @nestjs/microservices (TCP), TypeORM, @nestjs/jwt, bcrypt, pnpm workspace, PostgreSQL 16

**设计文档:** `docs/superpowers/specs/2026-04-16-microservice-architecture-design.md`

**前置依赖:** 子计划 A 已完成（docker-compose.yml 中 PostgreSQL 已就绪）

**JWT 载荷规范（与 Java/Python 对齐）：**
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
backend-nestjs/
├── package.json                  # pnpm workspace 根
├── pnpm-workspace.yaml
├── tsconfig.base.json
├── .gitignore
├── gateway/
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts
│   │   ├── app.module.ts
│   │   ├── guards/
│   │   │   └── jwt-auth.guard.ts
│   │   ├── decorators/
│   │   │   └── current-user.decorator.ts
│   │   └── proxy/
│   │       └── auth-proxy.controller.ts
├── auth-service/
│   ├── package.json
│   ├── tsconfig.json
│   ├── src/
│   │   ├── main.ts
│   │   ├── app.module.ts
│   │   ├── auth/
│   │   │   ├── auth.controller.ts
│   │   │   ├── auth.service.ts
│   │   │   ├── jwt.provider.ts
│   │   │   └── dto/
│   │   │       ├── login.dto.ts
│   │   │       └── register.dto.ts
│   │   ├── user/
│   │   │   ├── user.entity.ts
│   │   │   └── user.repository.ts
│   │   ├── organization/
│   │   │   ├── organization.entity.ts
│   │   │   ├── organization-user.entity.ts
│   │   │   ├── organization-user-role.entity.ts
│   │   │   └── tenant.entity.ts
│   │   ├── rbac/
│   │   │   ├── role.entity.ts
│   │   │   └── permission.entity.ts
│   │   └── menu/
│   │       ├── menu.entity.ts
│   │       └── menu.service.ts
└── shared/
    ├── package.json
    ├── tsconfig.json
    └── src/
        ├── index.ts
        ├── constants.ts
        └── interfaces/
            └── identity.interface.ts
```

---

## Task 1: 初始化 pnpm workspace

**Files:**
- Create: `backend-nestjs/pnpm-workspace.yaml`
- Create: `backend-nestjs/package.json`
- Create: `backend-nestjs/tsconfig.base.json`
- Create: `backend-nestjs/.gitignore`

- [ ] **Step 1: 创建 workspace 配置**

```yaml
# backend-nestjs/pnpm-workspace.yaml
packages:
  - 'gateway'
  - 'auth-service'
  - 'shared'
```

```json
// backend-nestjs/package.json
{
  "name": "cdm-backend-nestjs",
  "private": true,
  "scripts": {
    "dev:gateway": "pnpm --filter gateway run start:dev",
    "dev:auth": "pnpm --filter auth-service run start:dev",
    "build:all": "pnpm -r run build"
  }
}
```

```json
// backend-nestjs/tsconfig.base.json
{
  "compilerOptions": {
    "module": "commonjs",
    "target": "ES2021",
    "lib": ["ES2021"],
    "declaration": true,
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "moduleResolution": "node",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "emitDecoratorMetadata": true,
    "experimentalDecorators": true
  }
}
```

```gitignore
# backend-nestjs/.gitignore
node_modules/
dist/
.env
```

- [ ] **Step 2: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/
git commit -m "feat(nestjs): 初始化 pnpm workspace monorepo"
```

---

## Task 2: 创建 shared 库

**Files:**
- Create: `backend-nestjs/shared/package.json`
- Create: `backend-nestjs/shared/tsconfig.json`
- Create: `backend-nestjs/shared/src/index.ts`
- Create: `backend-nestjs/shared/src/constants.ts`
- Create: `backend-nestjs/shared/src/interfaces/identity.interface.ts`

- [ ] **Step 1: 创建 shared 包配置与代码**

```json
// backend-nestjs/shared/package.json
{
  "name": "@cdm/shared",
  "version": "0.1.0",
  "main": "src/index.ts",
  "scripts": {
    "build": "tsc"
  }
}
```

```json
// backend-nestjs/shared/tsconfig.json
{
  "extends": "../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"]
}
```

```typescript
// backend-nestjs/shared/src/constants.ts
export const AUTH_SERVICE = 'AUTH_SERVICE';
export const PATIENT_SERVICE = 'PATIENT_SERVICE';
export const CHAT_SERVICE = 'CHAT_SERVICE';

export const AUTH_TCP_PORT = 8011;
export const PATIENT_TCP_PORT = 8021;
export const CHAT_TCP_PORT = 8031;
```

```typescript
// backend-nestjs/shared/src/interfaces/identity.interface.ts
export interface IdentityPayload {
  userId: number;
  tenantId: number;
  orgId: number;
  roles: string[];
}
```

```typescript
// backend-nestjs/shared/src/index.ts
export * from './constants';
export * from './interfaces/identity.interface';
```

- [ ] **Step 2: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/shared/
git commit -m "feat(nestjs): shared 库（常量、接口定义）"
```

---

## Task 3: 创建 auth-service 微服务

**Files:**
- Create: `backend-nestjs/auth-service/package.json`
- Create: `backend-nestjs/auth-service/tsconfig.json`
- Create: `backend-nestjs/auth-service/src/main.ts`
- Create: `backend-nestjs/auth-service/src/app.module.ts`
- Create: 所有实体类和 DTO

- [ ] **Step 1: 创建 auth-service 包配置**

```json
// backend-nestjs/auth-service/package.json
{
  "name": "auth-service",
  "version": "0.1.0",
  "scripts": {
    "build": "nest build",
    "start:dev": "nest start --watch",
    "start:prod": "node dist/main"
  },
  "dependencies": {
    "@nestjs/common": "^10.0.0",
    "@nestjs/core": "^10.0.0",
    "@nestjs/microservices": "^10.0.0",
    "@nestjs/typeorm": "^10.0.0",
    "@nestjs/jwt": "^10.0.0",
    "typeorm": "^0.3.20",
    "pg": "^8.13.0",
    "bcrypt": "^5.1.1",
    "class-validator": "^0.14.0",
    "class-transformer": "^0.5.1",
    "reflect-metadata": "^0.2.0",
    "rxjs": "^7.8.0",
    "@cdm/shared": "workspace:*"
  },
  "devDependencies": {
    "@nestjs/cli": "^10.0.0",
    "@types/bcrypt": "^5.0.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.4.0"
  }
}
```

```json
// backend-nestjs/auth-service/tsconfig.json
{
  "extends": "../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 2: 创建入口与模块**

```typescript
// backend-nestjs/auth-service/src/main.ts
import { NestFactory } from '@nestjs/core';
import { Transport, MicroserviceOptions } from '@nestjs/microservices';
import { AppModule } from './app.module';
import { AUTH_TCP_PORT } from '@cdm/shared';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(
    AppModule,
    {
      transport: Transport.TCP,
      options: { host: '0.0.0.0', port: AUTH_TCP_PORT },
    },
  );
  await app.listen();
  console.log(`Auth service listening on TCP port ${AUTH_TCP_PORT}`);
}
bootstrap();
```

```typescript
// backend-nestjs/auth-service/src/app.module.ts
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { AuthController } from './auth/auth.controller';
import { AuthService } from './auth/auth.service';
import { JwtProvider } from './auth/jwt.provider';
import { MenuService } from './menu/menu.service';
import { UserEntity } from './user/user.entity';
import { TenantEntity } from './organization/tenant.entity';
import { OrganizationEntity } from './organization/organization.entity';
import { OrganizationUserEntity } from './organization/organization-user.entity';
import { OrganizationUserRoleEntity } from './organization/organization-user-role.entity';
import { RoleEntity } from './rbac/role.entity';
import { PermissionEntity } from './rbac/permission.entity';
import { MenuEntity } from './menu/menu.entity';

const entities = [
  UserEntity, TenantEntity, OrganizationEntity,
  OrganizationUserEntity, OrganizationUserRoleEntity,
  RoleEntity, PermissionEntity, MenuEntity,
];

@Module({
  imports: [
    TypeOrmModule.forRoot({
      type: 'postgres',
      host: process.env.DB_HOST || 'localhost',
      port: parseInt(process.env.DB_PORT || '5432'),
      username: process.env.DB_USER || 'postgres',
      password: process.env.DB_PASS || 'postgres',
      database: process.env.DB_NAME || 'ai_saas',
      entities,
      synchronize: false, // DDL 由 Alembic 管理
    }),
    TypeOrmModule.forFeature(entities),
    JwtModule.register({
      secret: process.env.JWT_SECRET || 'your-jwt-secret-here-must-match-python',
      signOptions: { expiresIn: '7d' },
    }),
  ],
  controllers: [AuthController],
  providers: [AuthService, JwtProvider, MenuService],
})
export class AppModule {}
```

- [ ] **Step 3: 创建实体类**

```typescript
// backend-nestjs/auth-service/src/user/user.entity.ts
import { Entity, Column, PrimaryColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('users')
export class UserEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ unique: true, length: 255 })
  email: string;

  @Column({ name: 'password_hash', length: 255, nullable: true })
  passwordHash: string;

  @Column({ length: 255, nullable: true })
  name: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
```

```typescript
// backend-nestjs/auth-service/src/organization/tenant.entity.ts
import { Entity, Column, PrimaryColumn, CreateDateColumn } from 'typeorm';

@Entity('tenants')
export class TenantEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ length: 255 })
  name: string;

  @Column({ unique: true, length: 100 })
  slug: string;

  @Column({ name: 'plan_type', length: 50, default: 'free' })
  planType: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
```

```typescript
// backend-nestjs/auth-service/src/organization/organization.entity.ts
import { Entity, Column, PrimaryColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('organizations')
export class OrganizationEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;

  @Column({ name: 'parent_id', type: 'bigint', nullable: true })
  parentId: number | null;

  @Column({ length: 255 })
  name: string;

  @Column({ length: 50 })
  code: string;

  @Column({ length: 20, default: 'active' })
  status: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
```

```typescript
// backend-nestjs/auth-service/src/organization/organization-user.entity.ts
import { Entity, Column, PrimaryColumn, CreateDateColumn } from 'typeorm';

@Entity('organization_users')
export class OrganizationUserEntity {
  @PrimaryColumn({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @PrimaryColumn({ name: 'user_id', type: 'bigint' })
  userId: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;

  @Column({ name: 'user_type', length: 20, default: 'staff' })
  userType: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
```

```typescript
// backend-nestjs/auth-service/src/organization/organization-user-role.entity.ts
import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('organization_user_roles')
export class OrganizationUserRoleEntity {
  @PrimaryColumn({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @PrimaryColumn({ name: 'user_id', type: 'bigint' })
  userId: number;

  @PrimaryColumn({ name: 'role_id', type: 'bigint' })
  roleId: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;
}
```

```typescript
// backend-nestjs/auth-service/src/rbac/role.entity.ts
import {
  Entity, Column, PrimaryColumn, ManyToMany, JoinTable,
  CreateDateColumn, UpdateDateColumn,
} from 'typeorm';
import { PermissionEntity } from './permission.entity';

@Entity('roles')
export class RoleEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'tenant_id', type: 'bigint', nullable: true })
  tenantId: number | null;

  @Column({ name: 'parent_role_id', type: 'bigint', nullable: true })
  parentRoleId: number | null;

  @Column({ length: 100 })
  name: string;

  @Column({ length: 100 })
  code: string;

  @Column({ name: 'is_system', default: false })
  isSystem: boolean;

  @ManyToMany(() => PermissionEntity)
  @JoinTable({
    name: 'role_permissions',
    joinColumn: { name: 'role_id' },
    inverseJoinColumn: { name: 'permission_id' },
  })
  permissions: PermissionEntity[];

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
```

```typescript
// backend-nestjs/auth-service/src/rbac/permission.entity.ts
import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('permissions')
export class PermissionEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ length: 100 })
  name: string;

  @Column({ unique: true, length: 100 })
  code: string;

  @Column({ name: 'resource_id', type: 'bigint' })
  resourceId: number;

  @Column({ name: 'action_id', type: 'bigint' })
  actionId: number;
}
```

```typescript
// backend-nestjs/auth-service/src/menu/menu.entity.ts
import { Entity, Column, PrimaryColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('menus')
export class MenuEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'parent_id', type: 'bigint', nullable: true })
  parentId: number | null;

  @Column({ name: 'tenant_id', type: 'bigint', nullable: true })
  tenantId: number | null;

  @Column({ length: 100 })
  name: string;

  @Column({ unique: true, length: 100 })
  code: string;

  @Column({ name: 'menu_type', length: 20, default: 'page' })
  menuType: string;

  @Column({ length: 255, nullable: true })
  path: string | null;

  @Column({ length: 50, nullable: true })
  icon: string | null;

  @Column({ name: 'permission_code', length: 100, nullable: true })
  permissionCode: string | null;

  @Column({ default: 0 })
  sort: number;

  @Column({ name: 'is_visible', default: true })
  isVisible: boolean;

  @Column({ name: 'is_enabled', default: true })
  isEnabled: boolean;

  @Column({ type: 'jsonb', nullable: true })
  meta: Record<string, any> | null;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
```

- [ ] **Step 4: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/auth-service/
git commit -m "feat(nestjs): auth-service 实体类 + 模块配置"
```

---

## Task 4: Auth Service — DTO + JWT Provider + AuthService

**Files:**
- Create: DTO 文件
- Create: `jwt.provider.ts`
- Create: `auth.service.ts`
- Create: `menu.service.ts`

- [ ] **Step 1: 创建 DTO**

```typescript
// backend-nestjs/auth-service/src/auth/dto/login.dto.ts
import { IsEmail, IsNotEmpty, IsString } from 'class-validator';

export class LoginDto {
  @IsEmail()
  username: string;

  @IsNotEmpty()
  @IsString()
  password: string;
}

export class RegisterDto {
  @IsEmail()
  email: string;

  @IsNotEmpty()
  @IsString()
  password: string;

  @IsString()
  name?: string;
}

export class SelectOrgDto {
  orgId: number;
  selectionToken: string;
}

export class SwitchOrgDto {
  orgId: number;
}
```

- [ ] **Step 2: 创建 JWT Provider**

```typescript
// backend-nestjs/auth-service/src/auth/jwt.provider.ts
import { Injectable } from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';

@Injectable()
export class JwtProvider {
  constructor(private readonly jwtService: JwtService) {}

  createAccessToken(
    userId: number,
    tenantId: number,
    orgId: number,
    roles: string[],
  ): string {
    return this.jwtService.sign({
      sub: String(userId),
      tenant_id: String(tenantId),
      org_id: String(orgId),
      roles,
    });
  }

  createSelectionToken(userId: number): string {
    return this.jwtService.sign(
      { sub: String(userId), purpose: 'org_selection' },
      { expiresIn: '5m' },
    );
  }

  parseToken(token: string): any {
    return this.jwtService.verify(token);
  }
}
```

- [ ] **Step 3: 创建 MenuService**

```typescript
// backend-nestjs/auth-service/src/menu/menu.service.ts
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, IsNull, Or, Equal } from 'typeorm';
import { MenuEntity } from './menu.entity';

interface MenuNode {
  id: number;
  name: string;
  code: string;
  menu_type: string;
  path: string | null;
  icon: string | null;
  permission_code: string | null;
  sort: number;
  is_visible: boolean;
  is_enabled: boolean;
  meta: Record<string, any> | null;
  children: MenuNode[];
}

@Injectable()
export class MenuService {
  constructor(
    @InjectRepository(MenuEntity)
    private readonly menuRepo: Repository<MenuEntity>,
  ) {}

  async getMenuTree(tenantId: number, permCodes: Set<string>): Promise<MenuNode[]> {
    const allMenus = await this.menuRepo.find({
      where: {
        isEnabled: true,
        tenantId: Or(IsNull(), Equal(tenantId)),
      },
      order: { sort: 'ASC' },
    });

    const visibleMenus = allMenus.filter(
      (m) => !m.permissionCode || permCodes.has(m.permissionCode),
    );

    return this.buildTree(visibleMenus);
  }

  private buildTree(menus: MenuEntity[]): MenuNode[] {
    const menuMap = new Map<number, MenuNode>();
    for (const m of menus) {
      menuMap.set(m.id, {
        id: m.id,
        name: m.name,
        code: m.code,
        menu_type: m.menuType,
        path: m.path,
        icon: m.icon,
        permission_code: m.permissionCode,
        sort: m.sort,
        is_visible: m.isVisible,
        is_enabled: m.isEnabled,
        meta: m.meta,
        children: [],
      });
    }

    const visibleIds = new Set(menuMap.keys());
    const roots: MenuNode[] = [];

    for (const m of menus) {
      const node = menuMap.get(m.id)!;
      if (m.parentId && visibleIds.has(m.parentId)) {
        menuMap.get(m.parentId)!.children.push(node);
      } else {
        roots.push(node);
      }
    }

    // 剪枝
    return roots.filter(
      (item) => item.menu_type !== 'directory' || item.children.length > 0,
    );
  }
}
```

- [ ] **Step 4: 创建 AuthService**

```typescript
// backend-nestjs/auth-service/src/auth/auth.service.ts
import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import * as bcrypt from 'bcrypt';
import { RpcException } from '@nestjs/microservices';
import { UserEntity } from '../user/user.entity';
import { OrganizationEntity } from '../organization/organization.entity';
import { OrganizationUserEntity } from '../organization/organization-user.entity';
import { OrganizationUserRoleEntity } from '../organization/organization-user-role.entity';
import { RoleEntity } from '../rbac/role.entity';
import { PermissionEntity } from '../rbac/permission.entity';
import { JwtProvider } from './jwt.provider';
import { MenuService } from '../menu/menu.service';
import { IdentityPayload } from '@cdm/shared';

@Injectable()
export class AuthService {
  constructor(
    @InjectRepository(UserEntity)
    private readonly userRepo: Repository<UserEntity>,
    @InjectRepository(OrganizationEntity)
    private readonly orgRepo: Repository<OrganizationEntity>,
    @InjectRepository(OrganizationUserEntity)
    private readonly orgUserRepo: Repository<OrganizationUserEntity>,
    @InjectRepository(OrganizationUserRoleEntity)
    private readonly orgUserRoleRepo: Repository<OrganizationUserRoleEntity>,
    @InjectRepository(RoleEntity)
    private readonly roleRepo: Repository<RoleEntity>,
    @InjectRepository(PermissionEntity)
    private readonly permRepo: Repository<PermissionEntity>,
    private readonly jwtProvider: JwtProvider,
    private readonly menuService: MenuService,
  ) {}

  async login(username: string, password: string) {
    const user = await this.userRepo.findOne({ where: { email: username } });
    if (!user || !this.verifyPassword(password, user.passwordHash)) {
      throw new RpcException({ statusCode: 422, message: 'Incorrect email or password' });
    }

    const orgUsers = await this.orgUserRepo.find({ where: { userId: user.id } });
    if (orgUsers.length === 0) {
      throw new RpcException({
        statusCode: 422,
        message: 'User is not a member of any active organization',
      });
    }

    if (orgUsers.length === 1) {
      const ou = orgUsers[0];
      const org = await this.orgRepo.findOneBy({ id: ou.orgId });
      const roleCodes = await this.getRoleCodes(ou.orgId, ou.userId);
      const token = this.jwtProvider.createAccessToken(
        user.id, org.tenantId, org.id, roleCodes,
      );
      return {
        access_token: token,
        token_type: 'bearer',
        organization: { id: org.id, name: org.name, tenant_id: org.tenantId },
        require_org_selection: false,
      };
    }

    // 多部门
    const selectionToken = this.jwtProvider.createSelectionToken(user.id);
    const orgList = await Promise.all(
      orgUsers.map(async (ou) => {
        const org = await this.orgRepo.findOneBy({ id: ou.orgId });
        return { id: org.id, name: org.name, tenant_id: org.tenantId };
      }),
    );

    return {
      access_token: null,
      token_type: 'bearer',
      organizations: orgList,
      require_org_selection: true,
      selection_token: selectionToken,
    };
  }

  async selectOrg(orgId: number, selectionToken: string) {
    let payload: any;
    try {
      payload = this.jwtProvider.parseToken(selectionToken);
      if (payload.purpose !== 'org_selection') {
        throw new Error();
      }
    } catch {
      throw new RpcException({ statusCode: 422, message: 'Invalid or expired selection token' });
    }

    const userId = Number(payload.sub);
    const ou = await this.orgUserRepo.findOne({ where: { orgId, userId } });
    if (!ou) {
      throw new RpcException({ statusCode: 403, message: 'User is not a member of this organization' });
    }

    const org = await this.orgRepo.findOneBy({ id: orgId });
    const roleCodes = await this.getRoleCodes(orgId, userId);
    const token = this.jwtProvider.createAccessToken(userId, org.tenantId, org.id, roleCodes);

    return {
      access_token: token,
      token_type: 'bearer',
      organization: { id: org.id, name: org.name, tenant_id: org.tenantId },
    };
  }

  async switchOrg(identity: IdentityPayload, orgId: number) {
    const ou = await this.orgUserRepo.findOne({
      where: { orgId, userId: identity.userId },
    });
    if (!ou) {
      throw new RpcException({ statusCode: 403, message: 'User is not a member of this organization' });
    }

    const org = await this.orgRepo.findOneBy({ id: orgId });
    const roleCodes = await this.getRoleCodes(orgId, identity.userId);
    const token = this.jwtProvider.createAccessToken(
      identity.userId, org.tenantId, org.id, roleCodes,
    );

    return {
      access_token: token,
      token_type: 'bearer',
      organization: { id: org.id, name: org.name, tenant_id: org.tenantId },
    };
  }

  async listMyOrgs(userId: number) {
    const orgUsers = await this.orgUserRepo.find({ where: { userId } });
    return Promise.all(
      orgUsers.map(async (ou) => {
        const org = await this.orgRepo.findOneBy({ id: ou.orgId });
        return { id: org.id, name: org.name, tenant_id: org.tenantId };
      }),
    );
  }

  async getMe(identity: IdentityPayload) {
    const user = await this.userRepo.findOneBy({ id: identity.userId });
    const perms = await this.getEffectivePermissions(identity.orgId, identity.userId);

    return {
      id: user.id,
      email: user.email,
      name: user.name,
      created_at: user.createdAt,
      tenant_id: identity.tenantId,
      org_id: identity.orgId,
      permissions: [...perms],
    };
  }

  async getMenuTree(identity: IdentityPayload) {
    const perms = await this.getEffectivePermissions(identity.orgId, identity.userId);
    return this.menuService.getMenuTree(identity.tenantId, perms);
  }

  // ── 私有方法 ──

  private verifyPassword(raw: string, hash: string): boolean {
    if (!hash) return false;
    if (hash.startsWith('$argon2')) return false; // Argon2 暂不支持
    return bcrypt.compareSync(raw, hash);
  }

  private async getRoleCodes(orgId: number, userId: number): Promise<string[]> {
    const ourList = await this.orgUserRoleRepo.find({ where: { orgId, userId } });
    const codes: string[] = [];
    for (const our of ourList) {
      const role = await this.roleRepo.findOneBy({ id: our.roleId });
      if (role) codes.push(role.code);
    }
    return codes;
  }

  private async getEffectivePermissions(orgId: number, userId: number): Promise<Set<string>> {
    const ourList = await this.orgUserRoleRepo.find({ where: { orgId, userId } });
    const roleIds = ourList.map((our) => our.roleId);

    // 展开继承链
    const allRoleIds = new Set(roleIds);
    const queue = [...roleIds];
    while (queue.length > 0) {
      const rid = queue.shift()!;
      const role = await this.roleRepo.findOneBy({ id: rid });
      if (role?.parentRoleId && !allRoleIds.has(role.parentRoleId)) {
        allRoleIds.add(role.parentRoleId);
        queue.push(role.parentRoleId);
      }
    }

    if (allRoleIds.size === 0) return new Set();

    // 查询所有角色的权限码
    const roles = await this.roleRepo.find({
      where: [...allRoleIds].map((id) => ({ id })),
      relations: ['permissions'],
    });

    const permCodes = new Set<string>();
    for (const role of roles) {
      for (const perm of role.permissions || []) {
        permCodes.add(perm.code);
      }
    }
    return permCodes;
  }
}
```

- [ ] **Step 5: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/auth-service/
git commit -m "feat(nestjs): auth-service DTO + JWT + AuthService + MenuService"
```

---

## Task 5: Auth Service — TCP Controller

**Files:**
- Create: `backend-nestjs/auth-service/src/auth/auth.controller.ts`

- [ ] **Step 1: 创建 TCP 消息处理控制器**

```typescript
// backend-nestjs/auth-service/src/auth/auth.controller.ts
import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { AuthService } from './auth.service';
import { IdentityPayload } from '@cdm/shared';

@Controller()
export class AuthController {
  constructor(private readonly authService: AuthService) {}

  @MessagePattern({ cmd: 'login' })
  async login(@Payload() data: { username: string; password: string }) {
    return this.authService.login(data.username, data.password);
  }

  @MessagePattern({ cmd: 'select_org' })
  async selectOrg(@Payload() data: { orgId: number; selectionToken: string }) {
    return this.authService.selectOrg(data.orgId, data.selectionToken);
  }

  @MessagePattern({ cmd: 'switch_org' })
  async switchOrg(@Payload() data: { identity: IdentityPayload; orgId: number }) {
    return this.authService.switchOrg(data.identity, data.orgId);
  }

  @MessagePattern({ cmd: 'my_orgs' })
  async myOrgs(@Payload() data: { identity: IdentityPayload }) {
    return this.authService.listMyOrgs(data.identity.userId);
  }

  @MessagePattern({ cmd: 'get_me' })
  async getMe(@Payload() data: { identity: IdentityPayload }) {
    return this.authService.getMe(data.identity);
  }

  @MessagePattern({ cmd: 'menu_tree' })
  async menuTree(@Payload() data: { identity: IdentityPayload }) {
    return this.authService.getMenuTree(data.identity);
  }
}
```

- [ ] **Step 2: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/auth-service/
git commit -m "feat(nestjs): auth-service TCP 消息控制器"
```

---

## Task 6: Gateway — HTTP 应用 + JWT Guard + 代理控制器

**Files:**
- Create: `backend-nestjs/gateway/package.json`
- Create: `backend-nestjs/gateway/tsconfig.json`
- Create: `backend-nestjs/gateway/src/main.ts`
- Create: `backend-nestjs/gateway/src/app.module.ts`
- Create: `backend-nestjs/gateway/src/guards/jwt-auth.guard.ts`
- Create: `backend-nestjs/gateway/src/decorators/current-user.decorator.ts`
- Create: `backend-nestjs/gateway/src/proxy/auth-proxy.controller.ts`

- [ ] **Step 1: 创建 gateway 包配置**

```json
// backend-nestjs/gateway/package.json
{
  "name": "gateway",
  "version": "0.1.0",
  "scripts": {
    "build": "nest build",
    "start:dev": "nest start --watch",
    "start:prod": "node dist/main"
  },
  "dependencies": {
    "@nestjs/common": "^10.0.0",
    "@nestjs/core": "^10.0.0",
    "@nestjs/microservices": "^10.0.0",
    "@nestjs/jwt": "^10.0.0",
    "@nestjs/platform-express": "^10.0.0",
    "class-validator": "^0.14.0",
    "class-transformer": "^0.5.1",
    "reflect-metadata": "^0.2.0",
    "rxjs": "^7.8.0",
    "@cdm/shared": "workspace:*"
  },
  "devDependencies": {
    "@nestjs/cli": "^10.0.0",
    "@types/node": "^20.0.0",
    "typescript": "^5.4.0"
  }
}
```

```json
// backend-nestjs/gateway/tsconfig.json
{
  "extends": "../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 2: 创建 Gateway 入口与模块**

```typescript
// backend-nestjs/gateway/src/main.ts
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalPipes(new ValidationPipe({ transform: true }));
  app.enableCors({
    origin: ['http://localhost:5173', 'http://localhost:3000'],
    credentials: true,
  });
  await app.listen(8001);
  console.log('NestJS Gateway listening on http://localhost:8001');
}
bootstrap();
```

```typescript
// backend-nestjs/gateway/src/app.module.ts
import { Module } from '@nestjs/common';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { JwtModule } from '@nestjs/jwt';
import { AUTH_SERVICE, AUTH_TCP_PORT } from '@cdm/shared';
import { AuthProxyController } from './proxy/auth-proxy.controller';

@Module({
  imports: [
    JwtModule.register({
      secret: process.env.JWT_SECRET || 'your-jwt-secret-here-must-match-python',
    }),
    ClientsModule.register([
      {
        name: AUTH_SERVICE,
        transport: Transport.TCP,
        options: { host: 'localhost', port: AUTH_TCP_PORT },
      },
    ]),
  ],
  controllers: [AuthProxyController],
})
export class AppModule {}
```

- [ ] **Step 3: 创建 JWT Guard**

```typescript
// backend-nestjs/gateway/src/guards/jwt-auth.guard.ts
import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { Request } from 'express';

@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(private readonly jwtService: JwtService) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<Request>();
    const authHeader = request.headers.authorization;
    if (!authHeader?.startsWith('Bearer ')) {
      throw new UnauthorizedException();
    }

    try {
      const token = authHeader.substring(7);
      const payload = this.jwtService.verify(token);
      // 将身份信息注入 request 对象
      (request as any).identity = {
        userId: Number(payload.sub),
        tenantId: Number(payload.tenant_id),
        orgId: Number(payload.org_id),
        roles: payload.roles || [],
      };
      return true;
    } catch {
      throw new UnauthorizedException();
    }
  }
}
```

- [ ] **Step 4: 创建 CurrentUser 装饰器**

```typescript
// backend-nestjs/gateway/src/decorators/current-user.decorator.ts
import { createParamDecorator, ExecutionContext } from '@nestjs/common';
import { IdentityPayload } from '@cdm/shared';

export const CurrentUser = createParamDecorator(
  (_data: unknown, ctx: ExecutionContext): IdentityPayload => {
    const request = ctx.switchToHttp().getRequest();
    return request.identity;
  },
);
```

- [ ] **Step 5: 创建 Auth 代理控制器**

```typescript
// backend-nestjs/gateway/src/proxy/auth-proxy.controller.ts
import {
  Body,
  Controller,
  Get,
  Inject,
  Post,
  UseGuards,
} from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom } from 'rxjs';
import { AUTH_SERVICE, IdentityPayload } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard';
import { CurrentUser } from '../decorators/current-user.decorator';

class LoginBody {
  username: string;
  password: string;
}

class SelectOrgBody {
  orgId: number;
  selectionToken: string;
}

class SwitchOrgBody {
  orgId: number;
}

@Controller('api/v1/auth')
export class AuthProxyController {
  constructor(
    @Inject(AUTH_SERVICE) private readonly authClient: ClientProxy,
  ) {}

  @Post('login/access-token')
  async login(@Body() body: LoginBody) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'login' }, body),
    );
  }

  @Post('select-org')
  async selectOrg(@Body() body: SelectOrgBody) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'select_org' }, body),
    );
  }

  @Post('switch-org')
  @UseGuards(JwtAuthGuard)
  async switchOrg(
    @Body() body: SwitchOrgBody,
    @CurrentUser() identity: IdentityPayload,
  ) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'switch_org' }, { identity, orgId: body.orgId }),
    );
  }

  @Get('my-orgs')
  @UseGuards(JwtAuthGuard)
  async myOrgs(@CurrentUser() identity: IdentityPayload) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'my_orgs' }, { identity }),
    );
  }

  @Get('me')
  @UseGuards(JwtAuthGuard)
  async me(@CurrentUser() identity: IdentityPayload) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'get_me' }, { identity }),
    );
  }

  @Get('menu-tree')
  @UseGuards(JwtAuthGuard)
  async menuTree(@CurrentUser() identity: IdentityPayload) {
    return firstValueFrom(
      this.authClient.send({ cmd: 'menu_tree' }, { identity }),
    );
  }
}
```

- [ ] **Step 6: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/gateway/
git commit -m "feat(nestjs): Gateway HTTP 应用 + JWT Guard + Auth 代理控制器"
```

---

## Task 7: 安装依赖与冒烟验证

- [ ] **Step 1: 安装所有依赖**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm install
```

Expected: 依赖安装成功，无报错

- [ ] **Step 2: 编译 shared 库**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm --filter @cdm/shared run build
```

Expected: 编译成功

- [ ] **Step 3: 编译 auth-service**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm --filter auth-service run build
```

Expected: 编译成功

- [ ] **Step 4: 编译 gateway**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm --filter gateway run build
```

Expected: 编译成功

- [ ] **Step 5: 提交最终状态**

```powershell
cd d:\codes\chronic-disease-management
git add -A
git commit -m "feat(nestjs): 完成第一期 Gateway + auth-service 构建验证"
```

---

## 自审检查

1. **设计文档覆盖**：覆盖了 P1-5（NestJS gateway + auth-service），API 端点与 Java 版完全对等（login、select-org、switch-org、my-orgs、me、menu-tree）。
2. **占位符扫描**：无 TBD/TODO。
3. **类型一致性**：JWT 载荷 `sub`/`tenant_id`/`org_id` 字符串格式与 Java/Python 对齐。`IdentityPayload` 接口在 shared 中定义，Gateway 和 auth-service 共用。
4. **与 Java 版差异**：
   - Gateway：Java 用声明式 YAML 路由 + GlobalFilter；NestJS 用编程式 Controller + ClientProxy
   - 内部通信：Java 用 HTTP；NestJS 用 TCP（@MessagePattern）
   - 鉴权传递：Java 注入 Header；NestJS 打包进 Payload 对象
   - 这些差异符合设计文档第 7.5 节的差异对照表
5. **密码兼容**：`verifyPassword` 检查 `$argon2` 前缀，Argon2 暂不支持，种子脚本需用 bcrypt 重新生成。
