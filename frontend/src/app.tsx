import { history } from '@umijs/max';
import { message, Space, Button } from 'antd';
import { getCurrentUser, getMenuTree } from './services/api/auth';
import React from 'react';

export const getInitialState = async (): Promise<any> => {
  const token = localStorage.getItem('token');
  if (!token) {
    if (window.location.pathname !== '/user/login') {
      history.push('/user/login');
    }
    return { currentUser: null, menuTree: [] };
  }
  
  try {
    const currentUser = await getCurrentUser();
    const menuTree = await getMenuTree();
    
    if (currentUser.org_id) {
      localStorage.setItem('currentOrgId', currentUser.org_id);
    }
    
    return { 
      currentUser, 
      menuTree,
      fetchUserInfo: getCurrentUser,
      fetchMenuTree: getMenuTree 
    };
  } catch {
    localStorage.removeItem('token');
    history.push('/user/login');
    return { currentUser: null, menuTree: [] };
  }
};

export const layout = ({ initialState }: any) => {
  return {
    logo: 'https://img.alicdn.com/tfs/TB1YHEpwUT1gK0jSZFhXXaAtVXa-28-27.svg',
    title: 'Chronic Disease AI',
    layout: 'mix',
    splitMenus: false,
    menu: {
      locale: false,
      request: async () => {
        // This effectively replaces static routes with dynamic ones from backend
        // We ensure the paths match .umirc.ts for Umi to render the correct component
        const { menuTree } = initialState || {};
        if (!menuTree || menuTree.length === 0) return [];
        
        return menuTree.map((item: any) => ({
          name: item.name,
          path: item.path,
          icon: item.icon,
          code: item.code,
        }));
      }
    },
    rightContentRender: () => {
      const user = initialState?.currentUser;
      if (!user) return null;
      return (
        <Space style={{ padding: '0 16px' }}>
          <span style={{ fontWeight: 500, color: 'rgba(0,0,0,0.65)' }}>
            {user.name || user.email}
          </span>
          <Button
            type="primary"
            danger
            size="small"
            ghost
            onClick={() => {
              localStorage.removeItem('token');
              localStorage.removeItem('currentOrgId');
              history.push('/user/login');
            }}
          >
            Logout
          </Button>
        </Space>
      );
    },
    onPageChange: () => {
      const { location } = history;
      if (!initialState?.currentUser && location.pathname !== '/user/login') {
        history.push('/user/login');
      }
    },
  };
};

export const request = {
  timeout: 10000,
  requestInterceptors: [
    (config: any) => {
      const token = localStorage.getItem('token');
      if (token) {
        config.headers = {
          ...config.headers,
          Authorization: `Bearer ${token}`,
        };
      }
      // Ensure orgId is handled as a string
      const orgId = localStorage.getItem('currentOrgId');
      if (orgId && orgId !== 'undefined' && orgId !== 'null') {
        config.headers = {
          ...config.headers,
          'X-Organization-ID': String(orgId),
        };
      }
      return config;
    },
  ],
  errorConfig: {
    errorHandler: (error: any) => {
      const { response } = error;
      if (response?.status === 401) {
        localStorage.removeItem('token');
        history.push('/user/login');
        message.error('Session expired, please login again');
      } else if (response?.status === 403) {
        message.error('Access denied');
      } else {
        if (error.name !== 'CanceledError') {
          message.error(error.message || 'Request failed');
        }
      }
    },
  },
};
