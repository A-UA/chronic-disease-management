import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import LoginPage from './pages/login/LoginPage';
import MainLayout from './components/layout/MainLayout';
import { useAuthStore } from './stores/auth';

// 页面导入
import OrgManagement from './pages/admin/OrgManagement';
import KBManagement from './pages/org/KBManagement';
import PatientWorkbench from './pages/biz/PatientWorkbench';

const queryClient = new QueryClient();

// 路由守卫组件
const ProtectedRoute: React.FC<{ children: React.ReactNode; allowedRoles?: string[] }> = ({ children, allowedRoles }) => {
  const { token, user } = useAuthStore();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // 根据角色进行校验
  if (allowedRoles && !allowedRoles.some(role => user?.roles?.includes(role))) {
    return <Navigate to="/403" replace />;
  }

  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          
          <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
            <Route path="/" element={<div>仪表盘首页</div>} />
            
            <Route path="/admin/orgs" element={<OrgManagement />} />
            <Route path="/org/staff" element={<div>成员管理</div>} />
            <Route path="/org/kb" element={<KBManagement />} />
            <Route path="/biz/patients" element={<PatientWorkbench />} />
            <Route path="/biz/chat" element={<div>AI 咨询</div>} />
            <Route path="/audit" element={<div>审计日志</div>} />
            
            <Route path="/403" element={<div>403 无权访问</div>} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
};

export default App;
