import { request } from '@umijs/max';

/** 
 * 统一资源 API (Resource-Based API Services)
 */

/** 1. Organizations */
export async function listOrganizations(params: any) {
  return request('/api/organizations', { method: 'GET', params });
}
export async function createOrganization(data: any) {
  return request('/api/organizations', { method: 'POST', data });
}
export async function getMyOrganizations() {
  return request('/api/organizations/me', { method: 'GET' });
}

/** 2. Users & Members */
export async function listAllUsers(params: any) {
  return request('/api/users', { method: 'GET', params });
}
export async function listOrgMembers(orgId: number) {
  return request(`/api/organizations/${orgId}/members`, { method: 'GET' });
}

/** 3. Patients */
export async function listPatients(params: any) {
  return request('/api/patients', { method: 'GET', params });
}
export async function getMyPatientProfile() {
  return request('/api/patients/me', { method: 'GET' });
}
export async function updateMyPatientProfile(data: any) {
  return request('/api/patients/me', { method: 'PUT', data });
}

/** 4. Dashboard & Stats */
export async function getDashboardStats() {
  return request('/api/dashboard/stats', { method: 'GET' });
}

/** 5. Knowledge Base & Docs */
export async function listKBs() {
  return request('/api/kb', { method: 'GET' });
}

/** 6. Audit & Usage */
export async function listAuditLogs(params: any) {
  return request('/api/audit-logs', { method: 'GET', params });
}
export async function getUsageSummary() {
  return request('/api/usage/summary', { method: 'GET' });
}

/** 7. System Settings */
export async function getSystemSettings() {
  return request('/api/settings', { method: 'GET' });
}
export async function updateSystemSettings(data: any) {
  return request('/api/settings', { method: 'PUT', data });
}
