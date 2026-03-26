import React, { useState } from 'react';
import { Layout, Menu, Button, theme, Typography, Dropdown, Space } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  DashboardOutlined,
  TeamOutlined,
  DatabaseOutlined,
  MessageOutlined,
  SettingOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAuthStore } from '../../stores/auth';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  // 根据角色过滤菜单
  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: '仪表盘',
      roles: ['SUPER_ADMIN', 'ORG_ADMIN', 'MANAGER'],
    },
    {
      key: '/admin/orgs',
      icon: <TeamOutlined />,
      label: '机构管理',
      roles: ['SUPER_ADMIN'],
    },
    {
      key: '/org/staff',
      icon: <TeamOutlined />,
      label: '成员管理',
      roles: ['ORG_ADMIN'],
    },
    {
      key: '/biz/patients',
      icon: <TeamOutlined />,
      label: '患者工作台',
      roles: ['MANAGER', 'ORG_ADMIN'],
    },
    {
      key: '/org/kb',
      icon: <DatabaseOutlined />,
      label: '知识库管理',
      roles: ['ORG_ADMIN', 'MANAGER'],
    },
    {
      key: '/biz/chat',
      icon: <MessageOutlined />,
      label: 'AI 咨询',
      roles: ['MANAGER', 'ORG_ADMIN'],
    },
    {
      key: '/audit',
      icon: <SettingOutlined />,
      label: '审计日志',
      roles: ['SUPER_ADMIN', 'ORG_ADMIN'],
    },
  ].filter(item => item.roles.some(role => user?.roles?.includes(role)));

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const userMenuItems = [
    {
      key: 'profile',
      label: '个人中心',
      icon: <UserOutlined />,
    },
    {
      key: 'logout',
      label: '退出登录',
      icon: <LogoutOutlined />,
      onClick: handleLogout,
    },
  ];

  return (
    <Layout className="min-h-screen">
      <Sider trigger={null} collapsible collapsed={collapsed}>
        <div className="flex items-center justify-center h-16 bg-[#002140]">
          <Title level={4} style={{ color: 'white', margin: 0, display: collapsed ? 'none' : 'block' }}>
            慢病管理后台
          </Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ padding: 0, background: colorBgContainer, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ fontSize: '16px', width: 64, height: 64 }}
          />
          <div style={{ paddingRight: 24 }}>
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Space className="cursor-pointer">
                <UserOutlined />
                <span>{user?.full_name || user?.username || '用户'}</span>
              </Space>
            </Dropdown>
          </div>
        </Header>
        <Content
          style={{
            margin: '24px 16px',
            padding: 24,
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            overflowY: 'auto'
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
