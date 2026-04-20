-- ============================================================
-- 慢病管理多租户 SaaS - 数据库初始化脚本
-- 数据库: PostgreSQL
-- 生成时间: 2026-04-17
-- 说明: 包含全部表结构定义 + 索引 + 种子数据
-- 使用方式: psql -h localhost -U postgres -d <数据库名> -f init.sql
-- ============================================================

-- ============================================================
-- 第一部分：表结构定义（按外键依赖顺序建表）
-- ============================================================

-- -----------------------------------------------------------
-- 1. tenants - 租户表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id          BIGINT       PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) NOT NULL UNIQUE,
    status      VARCHAR(20)  NOT NULL DEFAULT 'active',
    plan_type   VARCHAR(50)  NOT NULL DEFAULT 'free',
    created_at  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMP
);

-- -----------------------------------------------------------
-- 2. users - 用户表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id            BIGINT       PRIMARY KEY,
    email         VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255),
    name          VARCHAR(255),
    created_at    TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at    TIMESTAMP    NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users (email);

-- -----------------------------------------------------------
-- 3. organizations - 组织机构表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS organizations (
    id          BIGINT       PRIMARY KEY,
    tenant_id   BIGINT       NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    parent_id   BIGINT                REFERENCES organizations(id) ON DELETE SET NULL,
    name        VARCHAR(255) NOT NULL,
    code        VARCHAR(50)  NOT NULL,
    status      VARCHAR(20)  NOT NULL DEFAULT 'active',
    sort        INTEGER      NOT NULL DEFAULT 0,
    description TEXT,
    created_at  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMP,
    CONSTRAINT uq_org_tenant_code UNIQUE (tenant_id, code)
);
CREATE INDEX IF NOT EXISTS ix_organizations_tenant_id ON organizations (tenant_id);

-- -----------------------------------------------------------
-- 4. organization_users - 组织用户关联表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS organization_users (
    org_id     BIGINT      NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id    BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id  BIGINT      NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_type  VARCHAR(20) NOT NULL DEFAULT 'staff',
    created_at TIMESTAMP   NOT NULL DEFAULT now(),
    updated_at TIMESTAMP   NOT NULL DEFAULT now(),
    deleted_at TIMESTAMP,
    PRIMARY KEY (org_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_organization_users_tenant_id ON organization_users (tenant_id);

-- -----------------------------------------------------------
-- 5. roles - 角色表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS roles (
    id             BIGINT       PRIMARY KEY,
    tenant_id      BIGINT                REFERENCES tenants(id) ON DELETE CASCADE,
    parent_role_id BIGINT                REFERENCES roles(id) ON DELETE SET NULL,
    name           VARCHAR(100) NOT NULL,
    code           VARCHAR(100) NOT NULL,
    description    TEXT,
    is_system      BOOLEAN      NOT NULL DEFAULT false,
    created_at     TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at     TIMESTAMP    NOT NULL DEFAULT now(),
    deleted_at     TIMESTAMP,
    CONSTRAINT _tenant_role_code_uc UNIQUE (tenant_id, code)
);
CREATE INDEX IF NOT EXISTS ix_roles_tenant_id ON roles (tenant_id);
CREATE INDEX IF NOT EXISTS ix_roles_code ON roles (code);
CREATE INDEX IF NOT EXISTS ix_roles_name ON roles (name);

-- -----------------------------------------------------------
-- 6. organization_user_roles - 组织用户角色关联表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS organization_user_roles (
    org_id    BIGINT NOT NULL,
    user_id   BIGINT NOT NULL,
    role_id   BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    tenant_id BIGINT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    PRIMARY KEY (org_id, user_id, role_id)
);

-- -----------------------------------------------------------
-- 7. permissions - 权限表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS permissions (
    id          BIGINT       PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    code        VARCHAR(100) NOT NULL UNIQUE,
    resource_id BIGINT,
    action_id   BIGINT
);
CREATE INDEX IF NOT EXISTS ix_permissions_name ON permissions (name);

-- -----------------------------------------------------------
-- 8. role_permissions - 角色权限关联表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       BIGINT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id BIGINT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- -----------------------------------------------------------
-- 9. menus - 菜单表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS menus (
    id              BIGINT       PRIMARY KEY,
    parent_id       BIGINT                REFERENCES menus(id) ON DELETE CASCADE,
    tenant_id       BIGINT                REFERENCES tenants(id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    code            VARCHAR(100) NOT NULL UNIQUE,
    menu_type       VARCHAR(20)  NOT NULL DEFAULT 'page',
    path            VARCHAR(255),
    icon            VARCHAR(50),
    permission_code VARCHAR(100),
    sort            INTEGER      NOT NULL DEFAULT 0,
    is_visible      BOOLEAN      NOT NULL DEFAULT true,
    is_enabled      BOOLEAN      NOT NULL DEFAULT true,
    meta            JSONB,
    created_at      TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at      TIMESTAMP    NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_menus_parent_sort ON menus (parent_id, sort);
CREATE INDEX IF NOT EXISTS idx_menus_tenant_id ON menus (tenant_id);

-- -----------------------------------------------------------
-- 10. patient_profiles - 患者档案表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_profiles (
    id         BIGINT       PRIMARY KEY,
    tenant_id  BIGINT       NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    org_id     BIGINT       NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name       VARCHAR(255) NOT NULL,
    gender     VARCHAR(20),
    created_at TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at TIMESTAMP    NOT NULL DEFAULT now(),
    deleted_at TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_patient_profiles_tenant_id ON patient_profiles (tenant_id);
CREATE INDEX IF NOT EXISTS ix_patient_profiles_org_id ON patient_profiles (org_id);
CREATE INDEX IF NOT EXISTS idx_patient_profiles_tenant_org ON patient_profiles (tenant_id, org_id);

-- -----------------------------------------------------------
-- 11. health_metrics - 健康指标表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS health_metrics (
    id           BIGINT      PRIMARY KEY,
    tenant_id    BIGINT      NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    org_id       BIGINT      NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    patient_id   BIGINT      NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,
    metric_type  VARCHAR(50) NOT NULL,
    metric_value VARCHAR(255) NOT NULL,
    recorded_at  TIMESTAMP   NOT NULL,
    created_at   TIMESTAMP   NOT NULL DEFAULT now(),
    updated_at   TIMESTAMP   NOT NULL DEFAULT now(),
    deleted_at   TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_health_metrics_tenant_id ON health_metrics (tenant_id);
CREATE INDEX IF NOT EXISTS ix_health_metrics_org_id ON health_metrics (org_id);
CREATE INDEX IF NOT EXISTS ix_health_metrics_patient_id ON health_metrics (patient_id);
CREATE INDEX IF NOT EXISTS ix_health_metrics_metric_type ON health_metrics (metric_type);
CREATE INDEX IF NOT EXISTS idx_health_metrics_tenant_org ON health_metrics (tenant_id, org_id, patient_id);

-- -----------------------------------------------------------
-- 12. patient_family_links - 患者家属关联表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_family_links (
    id             BIGINT       PRIMARY KEY,
    tenant_id      BIGINT       NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    org_id         BIGINT       NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    patient_id     BIGINT       NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,
    family_user_id BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    relationship   VARCHAR(255) NOT NULL,
    created_at     TIMESTAMP    NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------
-- 13. patient_manager_assignments - 管理师分配表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS patient_manager_assignments (
    id              BIGINT       PRIMARY KEY,
    tenant_id       BIGINT       NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    org_id          BIGINT       NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    patient_id      BIGINT       NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,
    manager_user_id BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_type VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP    NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------
-- 14. management_suggestions - 管理建议表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS management_suggestions (
    id                 BIGINT       PRIMARY KEY,
    tenant_id          BIGINT       NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    org_id             BIGINT       NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    patient_id         BIGINT       NOT NULL REFERENCES patient_profiles(id) ON DELETE CASCADE,
    created_by_user_id BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    suggestion_type    VARCHAR(255) NOT NULL,
    content            TEXT         NOT NULL,
    status             VARCHAR(50)  NOT NULL DEFAULT 'pending',
    created_at         TIMESTAMP    NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------
-- 15. knowledge_bases - 知识库表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id          BIGINT    PRIMARY KEY,
    tenant_id   BIGINT       NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    org_id      BIGINT       NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    created_by  BIGINT       NOT NULL REFERENCES users(id),
    name        VARCHAR(255) NOT NULL,
    description TEXT,
    created_at  TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_knowledge_bases_tenant_id ON knowledge_bases (tenant_id);
CREATE INDEX IF NOT EXISTS ix_knowledge_bases_org_id ON knowledge_bases (org_id);

-- -----------------------------------------------------------
-- 16. documents - 文档表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id          BIGINT     PRIMARY KEY,
    tenant_id   BIGINT        NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    kb_id       BIGINT        NOT NULL REFERENCES knowledge_bases(id) ON DELETE CASCADE,
    org_id      BIGINT        NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    uploader_id BIGINT        NOT NULL REFERENCES users(id),
    file_name   VARCHAR(255)  NOT NULL,
    file_type   VARCHAR(50),
    file_size   INTEGER,
    minio_url   VARCHAR(1024) NOT NULL,
    status      VARCHAR(50)   NOT NULL DEFAULT 'processing',
    created_at  TIMESTAMP     NOT NULL DEFAULT now(),
    updated_at  TIMESTAMP     NOT NULL DEFAULT now(),
    deleted_at  TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_documents_tenant_id ON documents (tenant_id);
CREATE INDEX IF NOT EXISTS ix_documents_kb_id ON documents (kb_id);
CREATE INDEX IF NOT EXISTS idx_documents_tenant_kb ON documents (tenant_id, kb_id);

-- -----------------------------------------------------------
-- 17. conversations - 会话表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS conversations (
    id               BIGINT       PRIMARY KEY,
    tenant_id        BIGINT       NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    org_id           BIGINT       NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id          BIGINT       NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    kb_id            BIGINT       REFERENCES knowledge_bases(id) ON DELETE SET NULL,
    title            VARCHAR(100) NOT NULL DEFAULT '新对话',
    message_count    INTEGER      NOT NULL DEFAULT 0,
    total_tokens     INTEGER      NOT NULL DEFAULT 0,
    last_message_at  TIMESTAMP    NOT NULL DEFAULT now(),
    created_at       TIMESTAMP    NOT NULL DEFAULT now(),
    updated_at       TIMESTAMP    NOT NULL DEFAULT now(),
    deleted_at       TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_conversations_user
    ON conversations (tenant_id, user_id, last_message_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversations_org
    ON conversations (tenant_id, org_id);
CREATE INDEX IF NOT EXISTS idx_conversations_kb
    ON conversations (kb_id) WHERE kb_id IS NOT NULL;

-- -----------------------------------------------------------
-- 18. chat_messages - 聊天消息表
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
    id              BIGINT      PRIMARY KEY,
    conversation_id BIGINT      NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content         TEXT        NOT NULL,
    citations       JSONB,
    metadata        JSONB,
    token_count     INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMP   NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_conv
    ON chat_messages (conversation_id, created_at);


-- ============================================================
-- 第二部分：种子数据
-- ============================================================
-- ID 生成说明：
-- 项目使用雪花算法，参数：EPOCH=1704067200000(2024-01-01), workerBits=10, seqBits=12, workerId=1
-- 公式: ((timestamp - EPOCH) << 22) | (workerId << 12) | sequence
-- 种子 ID 使用固定时间戳 diff=60000ms (纪元后1分钟) 生成，位于时间线极早期，不会与业务数据冲突
-- 基础实体 base = (60000 << 22) | (1 << 12) = 2045078279118917632
-- 菜单实体 base = (60001 << 22) | (1 << 12) = 2045078279118917636

-- 默认租户 (seq=0)
INSERT INTO tenants (id, name, slug, plan_type) VALUES (2045078279118917632, '默认租户', 'default', 'free') ON CONFLICT DO NOTHING;

-- 总部医院组织 (seq=1)
INSERT INTO organizations (id, tenant_id, name, code, status) VALUES (2045078279118917633, 2045078279118917632, '总部医院', 'hq', 'active') ON CONFLICT DO NOTHING;

-- 系统管理员（密码: admin123）(seq=2)
INSERT INTO users (id, email, password_hash, name) VALUES (2045078279118917634, 'admin@cdm.com', '$2b$10$6maP.G1efHQ2Fy.UpOSHFugvFzPm4YDnMk58wNyqKsYTFaj8itB8C', '系统管理员') ON CONFLICT DO NOTHING;

-- 超管角色 (seq=3)
INSERT INTO roles (id, tenant_id, name, code, is_system) VALUES (2045078279118917635, 2045078279118917632, '超管', 'sysadmin', true) ON CONFLICT DO NOTHING;

-- 关联：管理员加入组织
INSERT INTO organization_users (org_id, user_id, tenant_id, user_type) VALUES (2045078279118917633, 2045078279118917634, 2045078279118917632, 'staff') ON CONFLICT DO NOTHING;

-- 关联：管理员分配超管角色
INSERT INTO organization_user_roles (org_id, user_id, role_id, tenant_id) VALUES (2045078279118917633, 2045078279118917634, 2045078279118917635, 2045078279118917632) ON CONFLICT DO NOTHING;

-- 菜单数据 (使用 diff=60001ms 的雪花 ID，base=2045078279118917636)
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(2045078279118917636, NULL,          NULL, '数据看板',       'dashboard',       'page',      '/dashboard',            'DashboardOutlined',         1,  true, true),
(2045078279118917637, NULL,          NULL, '患者管理',       'patient-list',   'page',      '/patients',             'UserOutlined',              10, true, true),
(2045078279118917638, NULL,          NULL, '知识摘要与文档', 'knowledge',       'directory', '/knowledge',            'BookOutlined',              20, true, true),
(2045078279118917639, 2045078279118917638,  NULL, '知识库管理',     'kb-list',         'page',      '/knowledge/list',       'AppstoreAddOutlined',       1,  true, true),
(2045078279118917640, 2045078279118917638,  NULL, '知识文档',       'kb-documents',    'page',      '/knowledge/documents',  'FileTextOutlined',          2,  true, true),
(2045078279118917641, NULL,          NULL, '智能问诊 Agent', 'ai-chat',         'page',      '/chat',                 'MessageOutlined',           30, true, true),
(2045078279118917642, NULL,          NULL, '系统管理',       'system',          'directory', '/system',               'SettingOutlined',           90, true, true),
(2045078279118917643, 2045078279118917642,  NULL, '用户管理',       'sys-users',       'page',      '/system/users',         'TeamOutlined',              1,  true, true),
(2045078279118917644, 2045078279118917642,  NULL, '租户管理',       'sys-tenants',     'page',      '/system/tenants',       'BankOutlined',              2,  true, true),
(2045078279118917645, 2045078279118917642,  NULL, '组织机构',       'sys-orgs',        'page',      '/system/orgs',          'ApartmentOutlined',         3,  true, true),
(2045078279118917646, 2045078279118917642,  NULL, '角色管理',       'sys-roles',       'page',      '/system/roles',         'SafetyCertificateOutlined', 4,  true, true),
(2045078279118917647, 2045078279118917642,  NULL, '菜单管理',       'sys-menus',       'page',      '/system/menus',         'MenuOutlined',              5,  true, true),
(2045078279118917648, 2045078279118917642,  NULL, '审计日志',       'sys-audit',       'page',      '/system/audit',         'AuditOutlined',             6,  true, true)
ON CONFLICT DO NOTHING;
