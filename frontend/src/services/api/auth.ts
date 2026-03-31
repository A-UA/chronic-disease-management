import { request } from '@umijs/max';

export async function login(email: string, password: string) {
  const formData = new URLSearchParams();
  formData.append('username', email);
  formData.append('password', password);
  return request('/api/auth/login/access-token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    data: formData.toString(),
  });
}

export async function register(email: string, password: string, name?: string) {
  return request('/api/auth/register', {
    method: 'POST',
    data: { email, password, name },
  });
}

export async function getCurrentUser() {
  return request('/api/auth/me', { method: 'GET' });
}

export async function getMenuTree() {
  return request('/api/auth/menu-tree', { method: 'GET' });
}
