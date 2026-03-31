import { defineConfig } from '@umijs/max';

export default defineConfig({
  antd: {},
  access: {},
  model: {},
  initialState: {},
  request: {},
  layout: {
    title: 'Chronic Disease AI',
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
    // Main Business Routes (Clean & Logical)
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', name: 'Dashboard', component: './organization/Dashboard' },
    { path: '/patients', name: 'Patients', component: './organization/Patients' },
    { path: '/knowledge', name: 'Knowledge', component: './organization/KnowledgeBases' },
    { path: '/chat', name: 'Chat', component: './organization/Conversations' },
    { path: '/members', name: 'Members', component: './organization/Members' },
    { path: '/roles', name: 'Roles', component: './organization/Roles' },
    { path: '/audit-logs', name: 'Audit', component: './organization/AuditLogs' },
    
    // Platform-level (Kept separate for super admins)
    {
      path: '/platform',
      name: 'Platform',
      icon: 'crown',
      routes: [
        { path: '/platform', redirect: '/platform/dashboard' },
        { path: '/platform/dashboard', component: './platform/Dashboard' },
        { path: '/platform/organizations', component: './platform/Organizations' },
        { path: '/platform/users', component: './platform/Users' },
        { path: '/platform/settings', component: './platform/Settings' },
      ],
    },
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
