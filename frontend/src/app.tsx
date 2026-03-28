import { history } from '@umijs/max';
import { message } from 'antd';
import { getCurrentUser } from './services/api/auth';

export const getInitialState = async (): Promise<any> => {
  const token = localStorage.getItem('token');
  if (!token) {
    return { currentUser: null };
  }
  try {
    const currentUser = await getCurrentUser();
    return { currentUser };
  } catch {
    localStorage.removeItem('token');
    return { currentUser: null };
  }
};

export const layout = ({ initialState }: any) => {
  return {
    logo: 'https://img.alicdn.com/tfs/TB1YHEpwUT1gK0jSZFhXXaAtVXa-28-27.svg',
    menu: {
      locale: false,
    },
    rightContentRender: () => {
      const user = initialState?.currentUser;
      if (!user) return null;
      return (
        <div style={{ padding: '0 16px', display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>{user.name || user.email}</span>
          <a
            onClick={() => {
              localStorage.removeItem('token');
              history.push('/user/login');
            }}
          >
            Logout
          </a>
        </div>
      );
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
      const orgId = localStorage.getItem('currentOrgId');
      if (orgId) {
        config.headers = {
          ...config.headers,
          'X-Organization-ID': orgId,
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
        message.error(error.message || 'Request failed');
      }
    },
  },
};
