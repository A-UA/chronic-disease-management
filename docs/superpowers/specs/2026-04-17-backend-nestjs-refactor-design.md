# Backend NestJS 微服务架构全面整改设计

> **决策日期**: 2026-04-17
> **整改范围**: 工程化基建 + 架构规范（全面整改）
> **整改策略**: 方案 2 — 全量重写（从零搭建骨架，业务代码原样迁入）

---

## 1. 背景与问题

当前 `backend-nestjs/` 存在以下工程化问题：

| 问题类别 | 具体表现 |
|---------|---------|
| **NestJS 版本混乱** | auth-service/gateway 用 `^10.0.0`，patient-service 用 `^11.0.1` |
| **TypeScript 配置不统一** | base 用 `commonjs/ES2021`，patient 独立用 `nodenext/ES2023`，patient 未继承 base |
| **严格模式不一致** | base `strictNullChecks: false`，patient `strictNullChecks: true` |
| **工程化工具缺失** | 无根级 ESLint/Prettier，只有 patient-service 局部配置 |
| **无构建编排** | 缺少 Turborepo/Nx 等 monorepo 构建工具 |
| **环境变量不一致** | auth 用 `DB_PASS`，patient 用 `DB_PASSWORD` |
| **ConfigModule 缺失** | auth-service 和 gateway 直接读 `process.env`，仅 patient 用 ConfigModule |
| **DTO 不规范** | gateway 的 DTO 内联在 Controller 中，无 class-validator 装饰器 |
| **目录命名不标准** | 顶级平铺 `auth-service/`、`patient-service/`，非 `apps/` + `libs/` 标准结构 |
| **脚手架残留** | patient-service 存在空的 app.controller/app.service |

## 2. 目标

1. 统一所有服务到 **NestJS 11.x** + **TypeScript 5.7+**
2. 重组为 **`apps/` + `libs/`** 行业标准 monorepo 结构
3. 引入 **Turborepo** 构建编排 + **根级 ESLint/Prettier** 统一代码规范
4. 统一 **`@nestjs/config`** 管理所有环境变量
5. 规范 **DTO 定义**（提取为独立文件 + class-validator 验证）
6. 清理所有脚手架残留代码

## 3. 目录结构

```
backend-nestjs/
├── apps/
│   ├── gateway/                    # 原 gateway/ → HTTP 网关
│   │   ├── src/
│   │   │   ├── main.ts
│   │   │   ├── app.module.ts
│   │   │   ├── guards/
│   │   │   │   └── jwt-auth.guard.ts
│   │   │   ├── decorators/
│   │   │   │   └── current-user.decorator.ts
│   │   │   └── proxy/
│   │   │       ├── dto/
│   │   │       │   ├── auth.dto.ts
│   │   │       │   ├── patient.dto.ts
│   │   │       │   ├── health-metric.dto.ts
│   │   │       │   └── ...
│   │   │       ├── auth-proxy.controller.ts
│   │   │       ├── patient-proxy.controller.ts
│   │   │       ├── health-metric-proxy.controller.ts
│   │   │       ├── ... (其他 proxy controllers)
│   │   │       └── services/
│   │   │           ├── minio-proxy.service.ts
│   │   │           └── agent-proxy.service.ts
│   │   ├── nest-cli.json
│   │   ├── package.json            # @cdm/gateway
│   │   └── tsconfig.json
│   ├── auth/                       # 原 auth-service/ → 去掉 -service 后缀
│   │   ├── src/
│   │   │   ├── main.ts
│   │   │   ├── app.module.ts
│   │   │   ├── auth/
│   │   │   │   ├── auth.controller.ts
│   │   │   │   ├── auth.service.ts
│   │   │   │   ├── jwt.provider.ts
│   │   │   │   └── dto/
│   │   │   ├── user/
│   │   │   │   └── user.entity.ts
│   │   │   ├── organization/
│   │   │   │   ├── tenant.entity.ts
│   │   │   │   ├── organization.entity.ts
│   │   │   │   ├── organization-user.entity.ts
│   │   │   │   └── organization-user-role.entity.ts
│   │   │   ├── rbac/
│   │   │   │   ├── role.entity.ts
│   │   │   │   └── permission.entity.ts
│   │   │   └── menu/
│   │   │       ├── menu.entity.ts
│   │   │       └── menu.service.ts
│   │   ├── nest-cli.json
│   │   ├── package.json            # @cdm/auth
│   │   └── tsconfig.json
│   └── patient/                    # 原 patient-service/ → 去掉 -service 后缀
│       ├── src/
│       │   ├── main.ts
│       │   ├── app.module.ts
│       │   ├── patient/
│       │   ├── health-metric/
│       │   ├── knowledge/
│       │   ├── management-suggestion/
│       │   ├── manager-assignment/
│       │   └── patient-family-link/
│       ├── nest-cli.json
│       ├── package.json            # @cdm/patient
│       └── tsconfig.json
├── libs/
│   └── shared/
│       ├── src/
│       │   ├── index.ts
│       │   ├── constants.ts
│       │   ├── config/
│       │   │   └── database.config.ts
│       │   ├── interfaces/
│       │   │   └── identity.interface.ts
│       │   ├── interceptors/
│       │   │   └── bigint-serializer.interceptor.ts
│       │   └── utils/
│       │       └── snowflake.ts
│       ├── package.json            # @cdm/shared
│       └── tsconfig.json
├── eslint.config.mjs               # 根级 ESLint flat config
├── .prettierrc                     # 根级 Prettier
├── tsconfig.base.json              # 统一 TS 基础配置
├── turbo.json                      # Turborepo 构建编排
├── pnpm-workspace.yaml             # PNPM Workspace
├── .gitignore
└── package.json                    # 根工作区
```

### 包命名

| 原包名 | 新包名 | 目录 |
|--------|--------|------|
| `gateway` | `@cdm/gateway` | `apps/gateway/` |
| `auth-service` | `@cdm/auth` | `apps/auth/` |
| `patient-service` | `@cdm/patient` | `apps/patient/` |
| `@cdm/shared` | `@cdm/shared` | `libs/shared/` |

## 4. 统一配置

### 4.1 TypeScript (`tsconfig.base.json`)

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

各子项目 `tsconfig.json` 统一模板：
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

### 4.2 环境变量

统一变量名：

| 变量 | 统一名称 |
|------|---------|
| 数据库主机 | `DB_HOST` |
| 数据库端口 | `DB_PORT` |
| 数据库用户 | `DB_USER` |
| 数据库密码 | `DB_PASSWORD` |
| 数据库名称 | `DB_NAME` |
| JWT 密钥 | `JWT_SECRET` |
| Auth TCP 端口 | `AUTH_TCP_PORT` |
| Patient TCP 端口 | `PATIENT_TCP_PORT` |

所有服务统一使用 `@nestjs/config` 的 `ConfigModule.forRoot()` 管理。

### 4.3 Turborepo (`turbo.json`)

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

### 4.4 PNPM Workspace

```yaml
packages:
  - 'apps/*'
  - 'libs/*'
```

### 4.5 根 `package.json`

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
    "globals": "^17.0.0"
  }
}
```

### 4.6 ESLint (`eslint.config.mjs`)

```javascript
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

### 4.7 Prettier (`.prettierrc`)

```json
{
  "singleQuote": true,
  "trailingComma": "all",
  "printWidth": 100,
  "tabWidth": 2,
  "semi": true
}
```

### 4.8 NestJS 统一版本

所有 apps 的 dependencies：
```json
{
  "@nestjs/common": "^11.0.1",
  "@nestjs/core": "^11.0.1",
  "@nestjs/config": "^4.0.0",
  "@nestjs/microservices": "^11.0.1",
  "@nestjs/platform-express": "^11.0.1",
  "@nestjs/typeorm": "^11.0.0",
  "@nestjs/jwt": "^11.0.0",
  "typeorm": "^0.3.20",
  "reflect-metadata": "^0.2.2",
  "rxjs": "^7.8.1"
}
```

各 app 独有依赖：
- **gateway**: `@nestjs/axios`, `axios`, `minio`, `uuid`, `form-data`, `class-validator`, `class-transformer`
- **auth**: `bcryptjs`, `class-validator`, `class-transformer`, `pg`
- **patient**: `pg`

### 4.9 各 App 的 `nest-cli.json`

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

## 5. 代码层面整治

### 5.1 Gateway DTO 提取

所有内联 DTO class 从 controller 中提取到 `proxy/dto/` 目录，添加 class-validator 装饰器。

示例 `apps/gateway/src/proxy/dto/auth.dto.ts`：
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

### 5.2 ConfigModule 统一

`libs/shared/src/config/database.config.ts`：
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

各 app 的 `app.module.ts` 使用 `TypeOrmModule.forRootAsync()` + `ConfigService` 替代硬编码。

### 5.3 shared 库扩展

新增 `config/database.config.ts`，需要 `@nestjs/config` 作为 peerDependency：
```json
{
  "peerDependencies": {
    "@nestjs/common": "^11.0.1",
    "@nestjs/config": "^4.0.0",
    "rxjs": "^7.8.1"
  }
}
```

### 5.4 清理

- 删除 patient-service 的 `app.controller.ts`、`app.service.ts`、`app.controller.spec.ts`
- 删除 patient-service 局部的 `eslint.config.mjs`、`.prettierrc`、`tsconfig.build.json`、`nest-cli.json`

## 6. 不改动的部分

以下内容原样迁移，不修改业务逻辑：

- `auth.service.ts` 全部业务逻辑
- `auth.controller.ts` 的 MessagePattern 定义
- `jwt-auth.guard.ts` 鉴权逻辑
- `jwt.provider.ts` JWT 工具
- `menu.service.ts` / `menu.entity.ts`
- 所有 entity 文件
- patient-service 下所有业务模块内部代码
- 所有 proxy controller 的路由和转发逻辑
- `snowflake.ts`、`bigint-serializer.interceptor.ts`

## 7. 验收标准

1. `pnpm install` 成功
2. `pnpm build` — 所有 apps 和 libs 编译通过
3. `pnpm dev:auth` → auth 微服务 TCP 监听成功
4. `pnpm dev:patient` → patient 微服务 TCP 监听成功
5. `pnpm dev:gateway` → gateway HTTP 监听成功
6. Gateway 可以代理请求到 auth/patient 微服务
7. `pnpm lint` 无错误
