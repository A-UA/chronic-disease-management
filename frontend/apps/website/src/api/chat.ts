import { apiClient } from "./client";

export interface ChatConversation {
  id: string;
  kbId: string;
  title: string | null;
  createdAt: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

export async function listConversations(): Promise<ChatConversation[]> {
  return apiClient.get("conversations").json<ChatConversation[]>();
}

export async function getConversation(
  id: string,
): Promise<{ id: string; title: string | null; messages: ChatMessage[] }> {
  return apiClient.get(`conversations/${id}`).json();
}

export async function deleteConversation(id: string): Promise<void> {
  await apiClient.delete(`conversations/${id}`);
}

/** 发起 SSE 流式聊天（返回原生 Response，调用方处理 EventSource） */
export async function sendChat(data: {
  kbId: string;
  query: string;
  conversationId?: string;
}): Promise<Response> {
  const token = localStorage.getItem("cdm_token");
  return fetch("/api/v1/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
  });
}
