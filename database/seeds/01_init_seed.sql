INSERT INTO tenants (id, name, slug, plan_type) VALUES (1, '默认租户', 'default', 'free') ON CONFLICT DO NOTHING;
INSERT INTO organizations (id, tenant_id, name, code, status) VALUES (1, 1, '总部医院', 'hq', 'active') ON CONFLICT DO NOTHING;
INSERT INTO users (id, email, password_hash, name) VALUES (1, 'admin@cdm.com', '$2b$10$6maP.G1efHQ2Fy.UpOSHFugvFzPm4YDnMk58wNyqKsYTFaj8itB8C', '系统管理员') ON CONFLICT DO NOTHING;
INSERT INTO roles (id, tenant_id, name, code, is_system) VALUES (1, 1, '超管', 'sysadmin', true) ON CONFLICT DO NOTHING;
INSERT INTO organization_users (org_id, user_id, tenant_id, user_type) VALUES (1, 1, 1, 'staff') ON CONFLICT DO NOTHING;
INSERT INTO organization_user_roles (org_id, user_id, role_id, tenant_id) VALUES (1, 1, 1, 1) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(1, NULL, NULL, '患者管理', 'patient-list', 'page', '/patients', 'UserOutlined', 10, true, true) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(2, NULL, NULL, '知识摘要与文档', 'knowledge', 'directory', '/knowledge', 'BookOutlined', 20, true, true) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(3, 2, NULL, '知识库管理', 'kb-list', 'page', '/knowledge/list', 'AppstoreAddOutlined', 1, true, true) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(4, 2, NULL, '知识文档', 'kb-documents', 'page', '/knowledge/documents', 'FileTextOutlined', 2, true, true) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(5, NULL, NULL, '智能问诊 Agent', 'ai-chat', 'page', '/chat', 'MessageOutlined', 30, true, true) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(6, NULL, NULL, '系统管理', 'system', 'directory', '/system', 'SettingOutlined', 90, true, true) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(7, 6, NULL, '用户管理', 'sys-users', 'page', '/system/users', 'TeamOutlined', 1, true, true) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(8, 6, NULL, '租户管理', 'sys-tenants', 'page', '/system/tenants', 'BankOutlined', 2, true, true) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(9, 6, NULL, '组织机构', 'sys-orgs', 'page', '/system/orgs', 'ApartmentOutlined', 3, true, true) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(10, 6, NULL, '角色管理', 'sys-roles', 'page', '/system/roles', 'SafetyCertificateOutlined', 4, true, true) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(11, 6, NULL, '菜单管理', 'sys-menus', 'page', '/system/menus', 'MenuOutlined', 5, true, true) ON CONFLICT DO NOTHING;
INSERT INTO menus (id, parent_id, tenant_id, name, code, menu_type, path, icon, sort, is_visible, is_enabled) VALUES
(12, 6, NULL, '审计日志', 'sys-audit', 'page', '/system/audit', 'AuditOutlined', 6, true, true) ON CONFLICT DO NOTHING;
