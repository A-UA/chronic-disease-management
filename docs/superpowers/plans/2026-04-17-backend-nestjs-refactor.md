# Backend NestJS 全面整改实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有碎片化的 NestJS 微服务 monorepo 全面重写为符合行业标准的 `apps/` + `libs/` 结构，统一 NestJS 11、TypeScript、ESLint/Prettier、Turborepo 等工程化配置，规范 DTO 和 ConfigModule 使用。

**Architecture:** 全量重写策略 — 在 `backend-nestjs/` 目录下清除旧结构、搭建全新骨架，然后将业务代码原样迁入新结构。

**Tech Stack:** NestJS 11, TypeScript 5.7+, TypeORM 0.3.x, PNPM Workspace, Turborepo 2.x, ESLint 9 flat config, Prettier 3.x

**Spec:** `docs/superpowers/specs/2026-04-17-backend-nestjs-refactor-design.md`

---

## Task 1: 创建 Git 工作分支

**Files:**
- Modify: `backend-nestjs/` (git operations)

- [ ] **Step 1: 创建并切换到重构分支**

```powershell
cd d:\codes\chronic-disease-management
git checkout -b feature/backend-nestjs-refactor
```

- [ ] **Step 2: 确认分支已切换**

Run: `git branch --show-current`
Expected: `feature/backend-nestjs-refactor`

---

## Task 2: 清除旧目录结构

**Files:**
- Delete: `backend-nestjs/auth-service/`
- Delete: `backend-nestjs/gateway/`
- Delete: `backend-nestjs/patient-service/`
- Delete: `backend-nestjs/shared/`
- Delete: `backend-nestjs/node_modules/`
- Delete: `backend-nestjs/pnpm-lock.yaml`
- Keep: `backend-nestjs/.gitignore`

> 注意：不要删除 `.gitignore`。旧的 `package.json`、`tsconfig.base.json`、`pnpm-workspace.yaml` 将被后续步骤覆盖。

- [ ] **Step 1: 删除旧的子项目目录和锁文件**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
Remove-Item -Recurse -Force auth-service, gateway, patient-service, shared, node_modules
Remove-Item -Force pnpm-lock.yaml
```

- [ ] **Step 2: 确认只留下骨架文件**

Run: `Get-ChildItem -Name`
Expected: 列表中只剩 `.gitignore`、`package.json`、`tsconfig.base.json`、`pnpm-workspace.yaml`

- [ ] **Step 3: 更新 .gitignore**

写入 `backend-nestjs/.gitignore`：

```gitignore
node_modules/
dist/
.turbo/
*.tsbuildinfo
.env
```

- [ ] **Step 4: 提交清理**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/
git commit -m "重构: 清除 backend-nestjs 旧目录结构"
```

---

## Task 3: 搭建 Monorepo 根配置

**Files:**
- Overwrite: `backend-nestjs/package.json`
- Overwrite: `backend-nestjs/pnpm-workspace.yaml`
- Overwrite: `backend-nestjs/tsconfig.base.json`
- Create: `backend-nestjs/turbo.json`
- Create: `backend-nestjs/.prettierrc`
- Create: `backend-nestjs/eslint.config.mjs`

- [ ] **Step 1: 写入根 package.json**

写入 `backend-nestjs/package.json`：

```json
{
  "name": "cdm-backend-nestjs",
  "private": true,
  "scripts": {
    "dev:gateway": "turbo run dev --filter=@cdm/gateway",
    "dev:auth": "turbo run dev --filter=@cdm/auth",
    "dev:patient": "turbo run dev --filter=@cdm/patient",
    "build": "turbo run build",
    "lint": "turbo run lint",
    "test": "turbo run test"
  },
  "devDependencies": {
    "turbo": "^2.5.0",
    "prettier": "^3.4.0",
    "eslint": "^9.18.0",
    "typescript-eslint": "^8.20.0",
    "@eslint/js": "^9.18.0",
    "eslint-plugin-prettier": "^5.2.0",
    "eslint-config-prettier": "^10.0.0",
    "globals": "^17.0.0",
    "typescript": "^5.7.3"
  }
}
```

- [ ] **Step 2: 写入 pnpm-workspace.yaml**

写入 `backend-nestjs/pnpm-workspace.yaml`：

```yaml
packages:
  - 'apps/*'
  - 'libs/*'
```

- [ ] **Step 3: 写入 tsconfig.base.json**

写入 `backend-nestjs/tsconfig.base.json`：

```json
{
  "compilerOptions": {
    "module": "NodeNext",
    "moduleResolution": "NodeNext",
    "target": "ES2023",
    "lib": ["ES2023"],
    "declaration": true,
    "strict": true,
    "strictNullChecks": true,
    "noImplicitAny": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "emitDecoratorMetadata": true,
    "experimentalDecorators": true,
    "incremental": true,
    "sourceMap": true,
    "removeComments": true
  }
}
```

- [ ] **Step 4: 写入 turbo.json**

写入 `backend-nestjs/turbo.json`：

```json
{
  "$schema": "https://turbo.build/schema.json",
  "tasks": {
    "build": {
      "dependsOn": ["^build"],
      "outputs": ["dist/**"]
    },
    "dev": {
      "cache": false,
      "persistent": true
    },
    "lint": {},
    "test": {
      "dependsOn": ["build"]
    }
  }
}
```

- [ ] **Step 5: 写入 .prettierrc**

写入 `backend-nestjs/.prettierrc`：

```json
{
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "semi": true
}
```

- [ ] **Step 6: 写入 eslint.config.mjs**

写入 `backend-nestjs/eslint.config.mjs`：

```javascript
// @ts-check
import eslint from '@eslint/js';
import tseslint from 'typescript-eslint';
import eslintPluginPrettierRecommended from 'eslint-plugin-prettier/recommended';
import globals from 'globals';

export default tseslint.config(
  { ignores: ['**/dist/**', '**/node_modules/**'] },
  eslint.configs.recommended,
  ...tseslint.configs.recommendedTypeChecked,
  eslintPluginPrettierRecommended,
  {
    languageOptions: {
      globals: { ...globals.node },
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-floating-promises': 'warn',
      '@typescript-eslint/no-unsafe-argument': 'warn',
      'prettier/prettier': ['error', { endOfLine: 'auto' }],
    },
  },
);
```

- [ ] **Step 7: 提交根配置**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/
git commit -m "重构: 搭建 monorepo 根配置 (Turborepo + ESLint + Prettier + TS)"
```

---

## Task 4: 搭建 libs/shared 包

**Files:**
- Create: `backend-nestjs/libs/shared/package.json`
- Create: `backend-nestjs/libs/shared/tsconfig.json`
- Create: `backend-nestjs/libs/shared/src/index.ts`
- Create: `backend-nestjs/libs/shared/src/constants.ts`
- Create: `backend-nestjs/libs/shared/src/interfaces/identity.interface.ts`
- Create: `backend-nestjs/libs/shared/src/interceptors/bigint-serializer.interceptor.ts`
- Create: `backend-nestjs/libs/shared/src/utils/snowflake.ts`
- Create: `backend-nestjs/libs/shared/src/config/database.config.ts`

- [ ] **Step 1: 创建 shared 的 package.json**

写入 `backend-nestjs/libs/shared/package.json`：

```json
{
  "name": "@cdm/shared",
  "version": "0.1.0",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch"
  },
  "dependencies": {
    "@sapphire/snowflake": "^3.5.5"
  },
  "peerDependencies": {
    "@nestjs/common": "^11.0.1",
    "@nestjs/config": "^4.0.0",
    "rxjs": "^7.8.1"
  },
  "devDependencies": {
    "typescript": "^5.7.3",
    "@nestjs/common": "^11.0.1",
    "@nestjs/config": "^4.0.0",
    "rxjs": "^7.8.1"
  }
}
```

- [ ] **Step 2: 创建 shared 的 tsconfig.json**

写入 `backend-nestjs/libs/shared/tsconfig.json`：

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 3: 创建 constants.ts**

写入 `backend-nestjs/libs/shared/src/constants.ts`：

```typescript
export const AUTH_SERVICE = 'AUTH_SERVICE';
export const PATIENT_SERVICE = 'PATIENT_SERVICE';
export const CHAT_SERVICE = 'CHAT_SERVICE';

export const AUTH_TCP_PORT = 8011;
export const PATIENT_TCP_PORT = 8021;
export const CHAT_TCP_PORT = 8031;

export const KNOWLEDGE_BASE_FIND_ALL = 'kb_find_all';
export const KNOWLEDGE_BASE_CREATE = 'kb_create';
export const KNOWLEDGE_BASE_STATS = 'kb_stats';
export const KNOWLEDGE_BASE_DELETE = 'kb_delete';

export const DOCUMENT_FIND_BY_KB = 'document_find_by_kb';
export const DOCUMENT_CREATE_SYNC = 'document_create_sync';
export const DOCUMENT_DELETE = 'document_delete';
```

- [ ] **Step 4: 创建 identity.interface.ts**

写入 `backend-nestjs/libs/shared/src/interfaces/identity.interface.ts`：

```typescript
export interface IdentityPayload {
  userId: number;
  tenantId: number;
  orgId: number;
  allowedOrgIds: number[];
  roles: string[];
}
```

- [ ] **Step 5: 创建 bigint-serializer.interceptor.ts**

写入 `backend-nestjs/libs/shared/src/interceptors/bigint-serializer.interceptor.ts`：

```typescript
import { CallHandler, ExecutionContext, Injectable, NestInterceptor } from '@nestjs/common';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';

/**
 * 将对象中可能存在的 bigint 或超出安全整数范围的数字转为字符串
 * 解决前端 JavaScript Number(>2^53) 精度丢失问题
 */
@Injectable()
export class BigIntSerializerInterceptor implements NestInterceptor {
  intercept(context: ExecutionContext, next: CallHandler): Observable<any> {
    return next.handle().pipe(
      map((data) => {
        if (!data) return data;
        return JSON.parse(
          JSON.stringify(data, (_, v) => {
            if (typeof v === 'bigint') {
              return v.toString();
            }
            return v;
          }),
        );
      }),
    );
  }
}
```

- [ ] **Step 6: 创建 snowflake.ts**

写入 `backend-nestjs/libs/shared/src/utils/snowflake.ts`：

```typescript
import { Snowflake } from '@sapphire/snowflake';

/**
 * 项目统一雪花 ID 生成器
 * 纪元: 1288834974657n (2010-11-04 09:42:54.657Z)
 * 与 Java 端 Hutool 默认纪元保持绝对一致，保证生成的 ID 长度和量级相同（19位数字）
 */
const CDM_EPOCH = 1288834974657n;
const snowflake = new Snowflake(CDM_EPOCH);

/**
 * 生成一个全局唯一的雪花 ID
 * 返回字符串形式以避免 JS 精度丢失，并在类型上兼容当前 Entity 定义
 */
export function nextId(): number {
  // trick: 运行时返回字符串给 TypeORM，满足 pg bigint 要求且无截断
  return snowflake.generate().toString() as unknown as number;
}

/**
 * 将 bigint 格式的 ID 转为字符串（用于 API 响应序列化）
 */
export function idToString(id: number | bigint): string {
  return String(id);
}
```

- [ ] **Step 7: 创建 database.config.ts**

写入 `backend-nestjs/libs/shared/src/config/database.config.ts`：

```typescript
import { registerAs } from '@nestjs/config';

export const databaseConfig = registerAs('database', () => ({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5432', 10),
  username: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  database: process.env.DB_NAME || 'ai_saas',
}));
```

- [ ] **Step 8: 创建 index.ts**

写入 `backend-nestjs/libs/shared/src/index.ts`：

```typescript
export * from './constants.js';
export * from './interfaces/identity.interface.js';
export { nextId, idToString } from './utils/snowflake.js';
export * from './interceptors/bigint-serializer.interceptor.js';
export { databaseConfig } from './config/database.config.js';
```

- [ ] **Step 9: 构建验证 shared 包**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm install --filter @cdm/shared
pnpm --filter @cdm/shared run build
```

Expected: 编译成功，`libs/shared/dist/` 下生成 `.js` 和 `.d.ts` 文件。

- [ ] **Step 10: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/libs/
git commit -m "重构: 创建 libs/shared 共享库 (constants/interfaces/interceptors/config)"
```

---

## Task 5: 搭建 apps/auth 服务

**Files:**
- Create: `backend-nestjs/apps/auth/package.json`
- Create: `backend-nestjs/apps/auth/tsconfig.json`
- Create: `backend-nestjs/apps/auth/nest-cli.json`
- Create: `backend-nestjs/apps/auth/src/main.ts`
- Create: `backend-nestjs/apps/auth/src/app.module.ts`
- Create: `backend-nestjs/apps/auth/src/auth/auth.controller.ts`
- Create: `backend-nestjs/apps/auth/src/auth/auth.service.ts`
- Create: `backend-nestjs/apps/auth/src/auth/jwt.provider.ts`
- Create: `backend-nestjs/apps/auth/src/auth/dto/login.dto.ts`
- Create: `backend-nestjs/apps/auth/src/user/user.entity.ts`
- Create: `backend-nestjs/apps/auth/src/organization/tenant.entity.ts`
- Create: `backend-nestjs/apps/auth/src/organization/organization.entity.ts`
- Create: `backend-nestjs/apps/auth/src/organization/organization-user.entity.ts`
- Create: `backend-nestjs/apps/auth/src/organization/organization-user-role.entity.ts`
- Create: `backend-nestjs/apps/auth/src/rbac/role.entity.ts`
- Create: `backend-nestjs/apps/auth/src/rbac/permission.entity.ts`
- Create: `backend-nestjs/apps/auth/src/menu/menu.entity.ts`
- Create: `backend-nestjs/apps/auth/src/menu/menu.service.ts`

- [ ] **Step 1: 创建 auth 的 package.json**

写入 `backend-nestjs/apps/auth/package.json`：

```json
{
  "name": "@cdm/auth",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build": "nest build",
    "dev": "nest start --watch",
    "start:prod": "node dist/main"
  },
  "dependencies": {
    "@cdm/shared": "workspace:*",
    "@nestjs/common": "^11.0.1",
    "@nestjs/core": "^11.0.1",
    "@nestjs/config": "^4.0.0",
    "@nestjs/jwt": "^11.0.0",
    "@nestjs/microservices": "^11.0.1",
    "@nestjs/typeorm": "^11.0.0",
    "bcryptjs": "^3.0.3",
    "class-transformer": "^0.5.1",
    "class-validator": "^0.14.0",
    "pg": "^8.13.0",
    "reflect-metadata": "^0.2.2",
    "rxjs": "^7.8.1",
    "typeorm": "^0.3.20"
  },
  "devDependencies": {
    "@nestjs/cli": "^11.0.0",
    "@nestjs/schematics": "^11.0.0",
    "@types/bcryptjs": "^3.0.0",
    "@types/node": "^22.0.0",
    "typescript": "^5.7.3"
  }
}
```

- [ ] **Step 2: 创建 auth 的 tsconfig.json**

写入 `backend-nestjs/apps/auth/tsconfig.json`：

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 3: 创建 auth 的 nest-cli.json**

写入 `backend-nestjs/apps/auth/nest-cli.json`：

```json
{
  "$schema": "https://json.schemastore.org/nest-cli",
  "collection": "@nestjs/schematics",
  "sourceRoot": "src",
  "compilerOptions": {
    "deleteOutDir": true
  }
}
```

- [ ] **Step 4: 创建 auth 的 main.ts**

写入 `backend-nestjs/apps/auth/src/main.ts`：

```typescript
import { NestFactory } from '@nestjs/core';
import { Transport, MicroserviceOptions } from '@nestjs/microservices';
import { AppModule } from './app.module.js';
import { AUTH_TCP_PORT } from '@cdm/shared';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.TCP,
    options: { host: '0.0.0.0', port: AUTH_TCP_PORT },
  });
  await app.listen();
  console.log(`Auth service listening on TCP port ${AUTH_TCP_PORT}`);
}
bootstrap();
```

- [ ] **Step 5: 创建 auth 的 app.module.ts**

写入 `backend-nestjs/apps/auth/src/app.module.ts`：

```typescript
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { databaseConfig } from '@cdm/shared';
import { AuthController } from './auth/auth.controller.js';
import { AuthService } from './auth/auth.service.js';
import { JwtProvider } from './auth/jwt.provider.js';
import { MenuService } from './menu/menu.service.js';
import { UserEntity } from './user/user.entity.js';
import { TenantEntity } from './organization/tenant.entity.js';
import { OrganizationEntity } from './organization/organization.entity.js';
import { OrganizationUserEntity } from './organization/organization-user.entity.js';
import { OrganizationUserRoleEntity } from './organization/organization-user-role.entity.js';
import { RoleEntity } from './rbac/role.entity.js';
import { PermissionEntity } from './rbac/permission.entity.js';
import { MenuEntity } from './menu/menu.entity.js';

const entities = [
  UserEntity,
  TenantEntity,
  OrganizationEntity,
  OrganizationUserEntity,
  OrganizationUserRoleEntity,
  RoleEntity,
  PermissionEntity,
  MenuEntity,
];

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [databaseConfig] }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        type: 'postgres',
        host: config.get<string>('database.host'),
        port: config.get<number>('database.port'),
        username: config.get<string>('database.username'),
        password: config.get<string>('database.password'),
        database: config.get<string>('database.database'),
        entities,
        synchronize: false,
      }),
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

- [ ] **Step 6: 迁移 auth 业务文件（原样复制，不改逻辑）**

以下文件从原代码原样复制到新路径，**仅修改 import 路径**（把相对路径中的旧路径改为新结构下的路径）：

- `auth-service/src/auth/auth.controller.ts` → `apps/auth/src/auth/auth.controller.ts`
- `auth-service/src/auth/auth.service.ts` → `apps/auth/src/auth/auth.service.ts`
- `auth-service/src/auth/jwt.provider.ts` → `apps/auth/src/auth/jwt.provider.ts`
- `auth-service/src/auth/dto/login.dto.ts` → `apps/auth/src/auth/dto/login.dto.ts`
- `auth-service/src/user/user.entity.ts` → `apps/auth/src/user/user.entity.ts`
- `auth-service/src/organization/tenant.entity.ts` → `apps/auth/src/organization/tenant.entity.ts`
- `auth-service/src/organization/organization.entity.ts` → `apps/auth/src/organization/organization.entity.ts`
- `auth-service/src/organization/organization-user.entity.ts` → `apps/auth/src/organization/organization-user.entity.ts`
- `auth-service/src/organization/organization-user-role.entity.ts` → `apps/auth/src/organization/organization-user-role.entity.ts`
- `auth-service/src/rbac/role.entity.ts` → `apps/auth/src/rbac/role.entity.ts`
- `auth-service/src/rbac/permission.entity.ts` → `apps/auth/src/rbac/permission.entity.ts`
- `auth-service/src/menu/menu.entity.ts` → `apps/auth/src/menu/menu.entity.ts`
- `auth-service/src/menu/menu.service.ts` → `apps/auth/src/menu/menu.service.ts`

注意：由于切换到 `NodeNext` module，所有**相对路径**的 import 需要加 `.js` 后缀。例如：
```typescript
// 旧
import { UserEntity } from '../user/user.entity';
// 新
import { UserEntity } from '../user/user.entity.js';
```

`@cdm/shared` 包导入不需要改（包导入走 `package.json` 的 `main` 字段）。

- [ ] **Step 7: 构建验证 auth**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm install --filter @cdm/auth
pnpm --filter @cdm/shared run build
pnpm --filter @cdm/auth run build
```

Expected: 编译成功，无错误。

- [ ] **Step 8: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/apps/auth/
git commit -m "重构: 创建 apps/auth 服务 (NestJS 11 + ConfigModule + 统一 tsconfig)"
```

---

## Task 6: 搭建 apps/patient 服务

**Files:**
- Create: `backend-nestjs/apps/patient/package.json`
- Create: `backend-nestjs/apps/patient/tsconfig.json`
- Create: `backend-nestjs/apps/patient/nest-cli.json`
- Create: `backend-nestjs/apps/patient/src/main.ts`
- Create: `backend-nestjs/apps/patient/src/app.module.ts`
- Migrate: patient 下所有业务模块（6个模块）

- [ ] **Step 1: 创建 patient 的 package.json**

写入 `backend-nestjs/apps/patient/package.json`：

```json
{
  "name": "@cdm/patient",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build": "nest build",
    "dev": "nest start --watch",
    "start:prod": "node dist/main",
    "test": "jest",
    "test:watch": "jest --watch",
    "test:cov": "jest --coverage"
  },
  "dependencies": {
    "@cdm/shared": "workspace:*",
    "@nestjs/common": "^11.0.1",
    "@nestjs/core": "^11.0.1",
    "@nestjs/config": "^4.0.0",
    "@nestjs/microservices": "^11.0.1",
    "@nestjs/typeorm": "^11.0.0",
    "pg": "^8.13.0",
    "reflect-metadata": "^0.2.2",
    "rxjs": "^7.8.1",
    "typeorm": "^0.3.20"
  },
  "devDependencies": {
    "@nestjs/cli": "^11.0.0",
    "@nestjs/schematics": "^11.0.0",
    "@nestjs/testing": "^11.0.1",
    "@types/jest": "^30.0.0",
    "@types/node": "^22.0.0",
    "jest": "^30.0.0",
    "ts-jest": "^29.2.5",
    "typescript": "^5.7.3"
  },
  "jest": {
    "moduleFileExtensions": ["js", "json", "ts"],
    "rootDir": "src",
    "testRegex": ".*\\.spec\\.ts$",
    "transform": { "^.+\\.(t|j)s$": "ts-jest" },
    "collectCoverageFrom": ["**/*.(t|j)s"],
    "coverageDirectory": "../coverage",
    "testEnvironment": "node"
  }
}
```

- [ ] **Step 2: 创建 patient 的 tsconfig.json 和 nest-cli.json**

写入 `backend-nestjs/apps/patient/tsconfig.json`：

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"]
}
```

写入 `backend-nestjs/apps/patient/nest-cli.json`：

```json
{
  "$schema": "https://json.schemastore.org/nest-cli",
  "collection": "@nestjs/schematics",
  "sourceRoot": "src",
  "compilerOptions": {
    "deleteOutDir": true
  }
}
```

- [ ] **Step 3: 创建 patient 的 main.ts**

写入 `backend-nestjs/apps/patient/src/main.ts`：

```typescript
import { NestFactory } from '@nestjs/core';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { AppModule } from './app.module.js';
import { PATIENT_TCP_PORT } from '@cdm/shared';

async function bootstrap() {
  const app = await NestFactory.createMicroservice<MicroserviceOptions>(AppModule, {
    transport: Transport.TCP,
    options: {
      host: '0.0.0.0',
      port: Number(process.env.PATIENT_TCP_PORT) || PATIENT_TCP_PORT,
    },
  });
  await app.listen();
  console.log(`Patient service listening on TCP port ${PATIENT_TCP_PORT}`);
}
bootstrap();
```

- [ ] **Step 4: 创建 patient 的 app.module.ts**

写入 `backend-nestjs/apps/patient/src/app.module.ts`：

```typescript
import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { databaseConfig } from '@cdm/shared';
import { PatientModule } from './patient/patient.module.js';
import { HealthMetricModule } from './health-metric/health-metric.module.js';
import { PatientFamilyLinkModule } from './patient-family-link/patient-family-link.module.js';
import { ManagerAssignmentModule } from './manager-assignment/manager-assignment.module.js';
import { ManagementSuggestionModule } from './management-suggestion/management-suggestion.module.js';
import { KnowledgeModule } from './knowledge/knowledge.module.js';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true, load: [databaseConfig] }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        type: 'postgres',
        host: config.get<string>('database.host'),
        port: config.get<number>('database.port'),
        username: config.get<string>('database.username'),
        password: config.get<string>('database.password'),
        database: config.get<string>('database.database'),
        autoLoadEntities: true,
        synchronize: false,
      }),
    }),
    PatientModule,
    HealthMetricModule,
    PatientFamilyLinkModule,
    ManagerAssignmentModule,
    ManagementSuggestionModule,
    KnowledgeModule,
  ],
})
export class AppModule {}
```

- [ ] **Step 5: 迁移 patient 业务模块**

将以下 6 个模块从 `patient-service/src/` 原样复制到 `apps/patient/src/`，仅修改相对路径 import：

1. `patient/` — patient.module.ts, patient.controller.ts, patient.service.ts, patient.entity.ts
2. `health-metric/` — health-metric.module.ts, health-metric.controller.ts, health-metric.service.ts, health-metric.entity.ts
3. `patient-family-link/` — 全套 4 文件
4. `manager-assignment/` — 全套 4 文件
5. `management-suggestion/` — 全套 4 文件
6. `knowledge/` — knowledge.module.ts, knowledge.controller.ts, knowledge.service.ts, entities/knowledge-base.entity.ts, entities/document.entity.ts

所有相对 import 加 `.js` 后缀。不迁移 `app.controller.ts`、`app.service.ts`、`app.controller.spec.ts`（脚手架残留）。

- [ ] **Step 6: 构建验证 patient**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm install --filter @cdm/patient
pnpm --filter @cdm/shared run build
pnpm --filter @cdm/patient run build
```

Expected: 编译成功。

- [ ] **Step 7: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/apps/patient/
git commit -m "重构: 创建 apps/patient 服务 (NestJS 11 + ConfigModule + 清理 boilerplate)"
```

---

## Task 7: 搭建 apps/gateway 服务

**Files:**
- Create: `backend-nestjs/apps/gateway/package.json`
- Create: `backend-nestjs/apps/gateway/tsconfig.json`
- Create: `backend-nestjs/apps/gateway/nest-cli.json`
- Create: `backend-nestjs/apps/gateway/src/main.ts`
- Create: `backend-nestjs/apps/gateway/src/app.module.ts`
- Create: `backend-nestjs/apps/gateway/src/guards/jwt-auth.guard.ts`
- Create: `backend-nestjs/apps/gateway/src/decorators/current-user.decorator.ts`
- Create: `backend-nestjs/apps/gateway/src/proxy/dto/auth.dto.ts`
- Migrate: 所有 proxy controllers 和 services

- [ ] **Step 1: 创建 gateway 的 package.json**

写入 `backend-nestjs/apps/gateway/package.json`：

```json
{
  "name": "@cdm/gateway",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build": "nest build",
    "dev": "nest start --watch",
    "start:prod": "node dist/main"
  },
  "dependencies": {
    "@cdm/shared": "workspace:*",
    "@nestjs/axios": "^4.0.1",
    "@nestjs/common": "^11.0.1",
    "@nestjs/core": "^11.0.1",
    "@nestjs/config": "^4.0.0",
    "@nestjs/jwt": "^11.0.0",
    "@nestjs/microservices": "^11.0.1",
    "@nestjs/platform-express": "^11.0.1",
    "axios": "^1.15.0",
    "class-transformer": "^0.5.1",
    "class-validator": "^0.14.0",
    "form-data": "^4.0.5",
    "minio": "^8.0.7",
    "reflect-metadata": "^0.2.2",
    "rxjs": "^7.8.1",
    "uuid": "^13.0.0"
  },
  "devDependencies": {
    "@nestjs/cli": "^11.0.0",
    "@nestjs/schematics": "^11.0.0",
    "@types/express": "^5.0.6",
    "@types/multer": "^2.1.0",
    "@types/node": "^22.0.0",
    "@types/uuid": "^11.0.0",
    "typescript": "^5.7.3"
  }
}
```

- [ ] **Step 2: 创建 gateway 的 tsconfig.json 和 nest-cli.json**

写入 `backend-nestjs/apps/gateway/tsconfig.json`：

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "./dist",
    "rootDir": "./src"
  },
  "include": ["src/**/*"]
}
```

写入 `backend-nestjs/apps/gateway/nest-cli.json`：

```json
{
  "$schema": "https://json.schemastore.org/nest-cli",
  "collection": "@nestjs/schematics",
  "sourceRoot": "src",
  "compilerOptions": {
    "deleteOutDir": true
  }
}
```

- [ ] **Step 3: 创建 gateway 的 main.ts**

写入 `backend-nestjs/apps/gateway/src/main.ts`：

```typescript
import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { AppModule } from './app.module.js';
import { BigIntSerializerInterceptor } from '@cdm/shared';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);
  app.useGlobalPipes(new ValidationPipe({ transform: true }));
  app.useGlobalInterceptors(new BigIntSerializerInterceptor());
  app.enableCors({
    origin: ['http://localhost:5173', 'http://localhost:3000'],
    credentials: true,
  });
  await app.listen(8001);
  console.log('NestJS Gateway listening on http://localhost:8001');
}
bootstrap();
```

- [ ] **Step 4: 创建 gateway 的 app.module.ts**

写入 `backend-nestjs/apps/gateway/src/app.module.ts`：

```typescript
import { Module } from '@nestjs/common';
import { ConfigModule } from '@nestjs/config';
import { ClientsModule, Transport } from '@nestjs/microservices';
import { JwtModule } from '@nestjs/jwt';
import { HttpModule } from '@nestjs/axios';
import { AUTH_SERVICE, AUTH_TCP_PORT, PATIENT_SERVICE, PATIENT_TCP_PORT } from '@cdm/shared';
import { AuthProxyController } from './proxy/auth-proxy.controller.js';
import { PatientProxyController } from './proxy/patient-proxy.controller.js';
import { HealthMetricProxyController } from './proxy/health-metric-proxy.controller.js';
import { PatientFamilyLinkProxyController } from './proxy/patient-family-link-proxy.controller.js';
import { ManagerAssignmentProxyController } from './proxy/manager-assignment-proxy.controller.js';
import { ManagementSuggestionProxyController } from './proxy/management-suggestion-proxy.controller.js';
import { KnowledgeBaseProxyController } from './proxy/knowledge-base-proxy.controller.js';
import { KnowledgeDocumentProxyController } from './proxy/knowledge-document-proxy.controller.js';
import { MinioProxyService } from './proxy/services/minio-proxy.service.js';
import { AgentProxyService } from './proxy/services/agent-proxy.service.js';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    JwtModule.register({
      secret: process.env.JWT_SECRET || 'your-jwt-secret-here-must-match-python',
    }),
    ClientsModule.register([
      {
        name: AUTH_SERVICE,
        transport: Transport.TCP,
        options: { host: 'localhost', port: AUTH_TCP_PORT },
      },
      {
        name: PATIENT_SERVICE,
        transport: Transport.TCP,
        options: { host: 'localhost', port: PATIENT_TCP_PORT },
      },
    ]),
    HttpModule,
  ],
  controllers: [
    AuthProxyController,
    PatientProxyController,
    HealthMetricProxyController,
    PatientFamilyLinkProxyController,
    ManagerAssignmentProxyController,
    ManagementSuggestionProxyController,
    KnowledgeBaseProxyController,
    KnowledgeDocumentProxyController,
  ],
  providers: [MinioProxyService, AgentProxyService],
})
export class AppModule {}
```

- [ ] **Step 5: 创建 gateway DTO 文件**

写入 `backend-nestjs/apps/gateway/src/proxy/dto/auth.dto.ts`：

```typescript
import { IsString, IsNotEmpty, IsNumber } from 'class-validator';

export class LoginDto {
  @IsString()
  @IsNotEmpty()
  username: string;

  @IsString()
  @IsNotEmpty()
  password: string;
}

export class SelectOrgDto {
  @IsNumber()
  orgId: number;

  @IsString()
  @IsNotEmpty()
  selectionToken: string;
}

export class SwitchOrgDto {
  @IsNumber()
  orgId: number;
}
```

- [ ] **Step 6: 迁移 gateway 的 guards、decorators、proxy controllers、services**

将以下文件迁移到新路径，修改 import（加 `.js` 后缀 + 使用 DTO 文件替代内联 class）：

- `guards/jwt-auth.guard.ts` → `apps/gateway/src/guards/jwt-auth.guard.ts`
- `decorators/current-user.decorator.ts` → `apps/gateway/src/decorators/current-user.decorator.ts`
- 所有 8 个 proxy controller → `apps/gateway/src/proxy/`
- `services/agent-proxy.service.ts` → `apps/gateway/src/proxy/services/agent-proxy.service.ts`
- `services/minio-proxy.service.ts` → `apps/gateway/src/proxy/services/minio-proxy.service.ts`

**auth-proxy.controller.ts 的关键改动**：删除内联的 `LoginBody`/`SelectOrgBody`/`SwitchOrgBody` class，改为从 `dto/auth.dto.js` 导入 `LoginDto`/`SelectOrgDto`/`SwitchOrgDto`。

- [ ] **Step 7: 构建验证 gateway**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm install --filter @cdm/gateway
pnpm --filter @cdm/shared run build
pnpm --filter @cdm/gateway run build
```

Expected: 编译成功。

- [ ] **Step 8: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add backend-nestjs/apps/gateway/
git commit -m "重构: 创建 apps/gateway 服务 (NestJS 11 + DTO 规范化 + ConfigModule)"
```

---

## Task 8: 全量安装与构建验证

**Files:**
- No new files

- [ ] **Step 1: 全量清理安装**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
pnpm install
```

Expected: 所有 workspace 包安装成功。

- [ ] **Step 2: 全量构建**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm build
```

Expected: `turbo run build` 按依赖顺序 (shared → auth/patient/gateway) 编译成功。

- [ ] **Step 3: 验证 build 产物**

```powershell
Get-ChildItem -Recurse -Name dist/main.js -Depth 4
```

Expected: 输出应包含：
- `libs/shared/dist/index.js`
- `apps/auth/dist/main.js`
- `apps/patient/dist/main.js`
- `apps/gateway/dist/main.js`

- [ ] **Step 4: 提交最终状态**

```powershell
cd d:\codes\chronic-disease-management
git add -A
git commit -m "重构: 完成 backend-nestjs 全量构建验证"
```

---

## Task 9: 运行时集成测试

**前置条件:** PostgreSQL 数据库已启动且 `database/init.sql` 已执行。

- [ ] **Step 1: 启动 auth 服务**

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm dev:auth
```

Expected: 控制台输出 `Auth service listening on TCP port 8011`

- [ ] **Step 2: 启动 patient 服务**（新终端）

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm dev:patient
```

Expected: 控制台输出 `Patient service listening on TCP port 8021`

- [ ] **Step 3: 启动 gateway**（新终端）

```powershell
cd d:\codes\chronic-disease-management\backend-nestjs
pnpm dev:gateway
```

Expected: 控制台输出 `NestJS Gateway listening on http://localhost:8001`

- [ ] **Step 4: 测试登录接口**

```powershell
Invoke-RestMethod -Method POST -Uri http://localhost:8001/api/v1/auth/login/access-token -ContentType 'application/json' -Body '{"username":"admin@example.com","password":"admin123"}'
```

Expected: 返回 JSON 包含 `access_token` 或合理的业务错误（如 422 用户不存在）。

- [ ] **Step 5: 停止服务，提交最终确认**

```powershell
cd d:\codes\chronic-disease-management
git add -A
git commit -m "重构: backend-nestjs 全面整改完成 - NestJS 11 / apps+libs / Turborepo / ESLint"
```

---

## Task 10: 更新 AGENTS.md

**Files:**
- Modify: `AGENTS.md`

- [ ] **Step 1: 更新 AGENTS.md 中 backend-nestjs 相关章节**

修改 `AGENTS.md` 中的目录结构描述，将旧的 `auth-service/`、`patient-service/`、`shared/` 替换为 `apps/auth/`、`apps/patient/`、`apps/gateway/`、`libs/shared/`。

更新启动命令：
```
pnpm dev:auth    → turbo run dev --filter=@cdm/auth
pnpm dev:patient → turbo run dev --filter=@cdm/patient
pnpm dev:gateway → turbo run dev --filter=@cdm/gateway
```

- [ ] **Step 2: 提交**

```powershell
cd d:\codes\chronic-disease-management
git add AGENTS.md
git commit -m "文档: 更新 AGENTS.md 反映 backend-nestjs 新目录结构"
```
