import { defineConfig } from '@umijs/max';

export default defineConfig({
  antd: {},
  access: {},
  model: {},
  initialState: {},
  request: {},
  layout: {
    title: 'Chronic Disease Admin',
    locale: false,
  },
  routes: [
    {
      path: '/user',
      layout: false,
      routes: [
        { path: '/user/login', component: './auth/Login' },
      ],
    },
    // Platform-level super admin
    {
      path: '/platform',
      name: 'Platform Admin',
      icon: 'crown',
      // access: 'canPlatformAdmin',
      routes: [
        { path: '/platform', redirect: '/platform/dashboard' },
        { path: '/platform/dashboard', name: 'Dashboard', component: './platform/Dashboard' },
        { path: '/platform/organizations', name: 'Organizations', component: './platform/Organizations' },
        { path: '/platform/users', name: 'Users', component: './platform/Users' },
        { path: '/platform/usage', name: 'Usage & Quota', component: './platform/Usage' },
        { path: '/platform/audit-logs', name: 'Audit Logs', component: './platform/AuditLogs' },
        { path: '/platform/settings', name: 'Settings', component: './platform/Settings' },
      ],
    },
    // Organization-level admin
    {
      path: '/org',
      name: 'Organization',
      icon: 'team',
      // access: 'canOrgAdmin',
      routes: [
        { path: '/org', redirect: '/org/dashboard' },
        { path: '/org/dashboard', name: 'Overview', component: './organization/Dashboard' },
        { path: '/org/members', name: 'Members', component: './organization/Members' },
        { path: '/org/roles', name: 'Roles & Permissions', component: './organization/Roles' },
        { path: '/org/patients', name: 'Patients', component: './organization/Patients' },
        { path: '/org/managers', name: 'Managers', component: './organization/Managers' },
        { path: '/org/knowledge-bases', name: 'Knowledge Bases', component: './organization/KnowledgeBases' },
        { path: '/org/conversations', name: 'Conversations', component: './organization/Conversations' },
        { path: '/org/usage', name: 'Usage', component: './organization/Usage' },
        { path: '/org/audit-logs', name: 'Audit Logs', component: './organization/AuditLogs' },
      ],
    },
    { path: '/', redirect: '/org/dashboard' },
    { component: './404' },
  ],
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      pathRewrite: { '^/api': '/api/v1' },
    },
  },
  npmClient: 'pnpm',
});
