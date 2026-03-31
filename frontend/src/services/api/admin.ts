import { request } from '@umijs/max';

/** Dashboard Stats */
export async function getDashboardStats() {
  return request('/api/admin/dashboard/stats', { method: 'GET' });
}

/** Organizations Management */
export async function listOrganizations(params: any) {
  return request('/api/admin/organizations', { method: 'GET', params });
}

export async function createOrganization(data: any) {
  return request('/api/admin/organizations', { method: 'POST', data });
}

/** User Management */
export async function listAllUsers(params: any) {
  return request('/api/admin/users', { method: 'GET', params });
}

/** Settings & System Pulse */
export async function getSystemSettings() {
  return request('/api/admin/settings', { method: 'GET' });
}

export async function updateSystemSettings(data: any) {
  return request('/api/admin/settings', { method: 'POST', data });
}

/** Audit Logs */
export async function listAuditLogs(params: any) {
  return request('/api/admin/audit-logs', { method: 'GET', params });
}
