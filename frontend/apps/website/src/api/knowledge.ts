import { apiClient } from "./client";

// ── 知识库 ──

export interface KnowledgeBase {
  id: string;
  name: string;
  description: string | null;
  document_count: number;
  chunk_count: number;
  created_at: string;
}

export interface KBCreateRequest {
  name: string;
  description?: string;
}

export async function listKBs(): Promise<KnowledgeBase[]> {
  return apiClient.get("kb").json<KnowledgeBase[]>();
}

export async function createKB(data: KBCreateRequest): Promise<KnowledgeBase> {
  return apiClient.post("kb", { json: data }).json<KnowledgeBase>();
}

export async function deleteKB(id: string): Promise<void> {
  await apiClient.delete(`kb/${id}`);
}

export async function getKBStats(
  id: string,
): Promise<{ document_count: number; chunk_count: number; total_tokens: number }> {
  return apiClient.get(`kb/${id}/stats`).json();
}

// ── 文档 ──

export interface KBDocument {
  id: string;
  kb_id: string;
  file_name: string;
  status: "pending" | "processing" | "completed" | "failed";
  failed_reason: string | null;
  chunk_count: number;
  created_at: string;
}

export async function listDocuments(kbId: string): Promise<KBDocument[]> {
  return apiClient.get(`documents/kb/${kbId}/documents`).json<KBDocument[]>();
}

export async function uploadDocument(kbId: string, file: File): Promise<KBDocument> {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.post(`documents/kb/${kbId}/documents`, { body: formData }).json<KBDocument>();
}

export async function deleteDocument(id: string): Promise<void> {
  await apiClient.delete(`documents/${id}`);
}
