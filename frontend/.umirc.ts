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
    // Unified Business Routes - Flat & Logical
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', name: 'Dashboard', component: './dashboard' },
    { path: '/patients', name: 'Patients', component: './patients' },
    { path: '/knowledge', name: 'Knowledge', component: './knowledge' },
    { path: '/chat', name: 'Chat', component: './chat' },
    { path: '/members', name: 'Members', component: './members' },
    { path: '/roles', name: 'Roles', component: './roles' },
    { path: '/audit-logs', name: 'Audit', component: './audit' },
    { path: '/usage', name: 'Usage', component: './usage' },
    
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
