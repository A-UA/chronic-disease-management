import { request } from '@umijs/max';

// Patients
export async function listPatients(params?: { skip?: number; limit?: number; search?: string }) {
  return request('/api/admin/patients/', { method: 'GET', params });
}

export async function getPatient(patientId: string) {
  return request(`/api/admin/patients/${patientId}`, { method: 'GET' });
}

export async function updatePatient(patientId: string, data: any) {
  return request(`/api/admin/patients/${patientId}`, { method: 'PUT', data });
}

// Managers
export async function listManagers() {
  return request('/api/admin/managers/', { method: 'GET' });
}

export async function getManagerPatients(managerId: string) {
  return request(`/api/admin/managers/${managerId}/patients`, { method: 'GET' });
}

export async function assignPatientToManager(data: {
  patient_id: string;
  manager_id: string;
  assignment_role?: string;
}) {
  return request('/api/admin/managers/assignments', { method: 'POST', data });
}

// Knowledge Bases
export async function listKnowledgeBases() {
  return request('/api/admin/knowledge-bases/', { method: 'GET' });
}

export async function listDocuments(kbId: string) {
  return request(`/api/admin/knowledge-bases/${kbId}/documents`, { method: 'GET' });
}

export async function deleteKnowledgeBase(kbId: string) {
  return request(`/api/admin/knowledge-bases/${kbId}`, { method: 'DELETE' });
}

export async function deleteDocument(docId: string) {
  return request(`/api/admin/knowledge-bases/documents/${docId}`, { method: 'DELETE' });
}

// Conversations
export async function listConversations(params?: { skip?: number; limit?: number }) {
  return request('/api/admin/conversations/', { method: 'GET', params });
}

export async function getConversationMessages(conversationId: string) {
  return request(`/api/admin/conversations/${conversationId}/messages`, { method: 'GET' });
}

// Org-level Audit Logs
export async function listOrgAuditLogs(params?: any) {
  return request('/api/admin/audit-logs/', { method: 'GET', params });
}

// Roles
export async function listRoles() {
  return request('/api/admin/roles/', { method: 'GET' });
}

export async function listPermissions() {
  return request('/api/admin/permissions/', { method: 'GET' });
}
