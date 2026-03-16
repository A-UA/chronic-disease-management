# B2B2C 医疗健康管理系统数据库设计文档

## 1. 业务背景与目标

本项目是一个面向 B 端医疗机构（医院、康养中心）及其 C 端用户（患者、管理师、家属）的 SaaS 平台。核心目标是实现多租户数据隔离、精细化的角色权限控制以及跨组织的数据授权访问。

## 2. 核心架构模式：B2B2C 多租户模型

### 2.1 账号体系
- **统一账号 (Unified Identity)**: 使用单一 `users` 表存储所有角色的基础认证信息（Email/手机号、密码哈希）。
- **角色解耦 (Role Decoupling)**: 用户的具体业务行为通过其在特定组织下的关联（`organization_users`）或其个人画像（`patient_profiles` / `family_profiles`）来定义。

### 2.2 数据隔离策略 (RLS)
- **组织内隔离**: 针对机构内部数据（如病历、问答），通过 PostgreSQL 的 **Row-Level Security (RLS)** 强制隔离 `org_id`。
- **跨组织授权**: “家属”通过外部关联表（`patient_family_links`）获得跨组织的受限访问权限，不强制要求家属属于特定机构。

## 3. 实体关系设计 (ERD)

### 3.1 基础与组织层
- **`organizations`**: B 端租户。
- **`users`**: 全局唯一账号表。
- **`organization_users`**: 机构成员表。存储管理师（Manager）、管理员（Admin）等机构内部身份。

### 3.2 角色画像层 (C-End Profiles)
- **`patient_profiles`**: 患者档案。
  - 属性：`org_id` (强绑定), `real_name`, `gender`, `birth_date`, `medical_info` (JSONB)。
- **`family_profiles`**: 家属档案。
  - 属性：`real_name`, `contact_info`。独立于机构存在。

### 3.3 动态关联层 (Linking Layer)
- **`patient_manager_assignments` (多对多)**: 
  - 关联患者与管理师团队。
  - 字段：`manager_id`, `patient_id`, `org_id`, `assignment_role` (主责/协助)。
- **`patient_family_links` (动态角色授权)**:
  - 关联患者与家属。
  - 字段：`patient_id`, `family_user_id`, `access_level` (1: 仅查看, 2: 可代办), `status` (pending/active)。

## 4. 数据库 Schema 定义 (SQLAlchemy 风格)

```python
# 1. 统一用户表
class User(Base):
    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]

# 2. 患者档案 (B端所属)
class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), unique=True)
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    real_name: Mapped[str]
    # RLS: org_id = current_setting('app.current_org_id')

# 3. 管理师分配表 (团队协同)
class PatientManagerAssignment(Base):
    __tablename__ = "patient_manager_assignments"
    org_id: Mapped[UUID] = mapped_column(ForeignKey("organizations.id"))
    manager_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patient_profiles.id"), primary_key=True)
    assignment_role: Mapped[str] # main, assistant

# 4. 家属绑定表 (跨组织动态授权)
class PatientFamilyLink(Base):
    __tablename__ = "patient_family_links"
    patient_id: Mapped[UUID] = mapped_column(ForeignKey("patient_profiles.id"), primary_key=True)
    family_user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    access_level: Mapped[int] # 1: ViewOnly, 2: ProxyAction
    status: Mapped[str] # pending, active, rejected
```

## 5. 权限与安全逻辑

### 5.1 管理师权限 (Manager)
- **查询逻辑**: `SELECT * FROM patient_profiles JOIN patient_manager_assignments ON ... WHERE manager_id = :current_user_id`。
- **约束**: 管理师仅能看到分配给自己的患者，且受其所在机构的 RLS 限制。

### 5.2 家属权限 (Family)
- **访问控制**: 家属请求数据时，系统解析 `patient_family_links`。
- **数据流**: 即使家属不属于机构 A，但通过 `access_level` 校验后，后端可以临时提升权限或绕过 RLS（在受控的服务层中）读取特定患者的数据。

### 5.3 患者权限 (Patient)
- **自我管理**: 患者通过 `user_id` 匹配自己的 `patient_profiles`，并可管理其家属的 `access_level`。

## 6. AI/RAG 集成点
- **上下文注入**: 当家属或管理师针对特定患者提问时，系统会基于 `patient_id` 自动挂载该患者的 `medical_info` 和历史问答作为 RAG 检索的参考上下文。
