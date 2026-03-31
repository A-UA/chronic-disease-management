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
    // Unified Business Routes - Flat & Resource Oriented
    { path: '/', redirect: '/dashboard' },
    
    // Core Resource Pages (Shared by all roles)
    { path: '/dashboard', name: 'Dashboard', component: './dashboard' },
    { path: '/patients', name: 'Patients', component: './patients' },
    { path: '/knowledge', name: 'Knowledge', component: './knowledge' },
    { path: '/chat', name: 'Chat', component: './chat' },
    
    // Management & Admin (B/C-side Unified)
    { path: '/members', name: 'Team', component: './members' },
    { path: '/roles', name: 'Permissions', component: './roles' },
    { path: '/audit-logs', name: 'Audit', component: './audit' },
    { path: '/usage', name: 'Usage', component: './usage' },
    { path: '/organizations', name: 'Organizations', component: './dashboard' }, // Placeholder for generic list
    { path: '/system-settings', name: 'System Settings', component: './dashboard' }, // Placeholder
    
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
