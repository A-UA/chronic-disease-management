import { request } from '@umijs/max';

// Dashboard
export async function getDashboardStats() {
  return request('/api/admin/dashboard/stats', { method: 'GET' });
}

// Organizations
export async function listOrganizations(params?: any) {
  return request('/api/admin/organizations/', { method: 'GET', params });
}

export async function createOrganization(data: { name: string; plan_type: string }) {
  return request('/api/admin/organizations/', { method: 'POST', data });
}

export async function updateOrganization(orgId: string | number, data: any) {
  return request(`/api/admin/organizations/${orgId}`, { method: 'PUT', data });
}

export async function deleteOrganization(orgId: string | number) {
  return request(`/api/admin/organizations/${orgId}`, { method: 'DELETE' });
}

export async function getMyOrganizations() {
  return request('/api/admin/organizations/me', { method: 'GET' });
}

export async function getOrganizationMembers(orgId: string | number) {
  return request(`/api/admin/organizations/${orgId}/members`, { method: 'GET' });
}

// Users
export async function listUsers(params?: { skip?: number; limit?: number; search?: string }) {
  return request('/api/admin/users/', { method: 'GET', params });
}

export async function updateUserStatus(userId: string | number, isActive: boolean) {
  return request(`/api/admin/users/${userId}/status`, {
    method: 'PUT',
    params: { is_active: isActive },
  });
}

// Usage
export async function getUsageSummary() {
  return request('/api/admin/usage/summary', { method: 'GET' });
}

export async function getOrgUsageDetail(orgId: string | number) {
  return request(`/api/admin/usage/by-organization/${orgId}`, { method: 'GET' });
}

// Audit Logs
export async function listAuditLogs(params?: any) {
  return request('/api/admin/audit-logs/', { method: 'GET', params });
}

// Settings
export async function getSettings() {
  return request('/api/admin/settings/', { method: 'GET' });
}

export async function updateSetting(key: string, value: string) {
  return request(`/api/admin/settings/${key}`, {
    method: 'PUT',
    data: { value },
  });
}
