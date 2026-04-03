import { apiClient } from "./client";
import type { TokenResponse, UserInfo, MenuItem } from "@/types/auth";

export async function loginApi(username: string, password: string): Promise<TokenResponse> {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);

  return apiClient
    .post("auth/login/access-token", {
      body: formData,
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    })
    .json<TokenResponse>();
}

export async function getMeApi(): Promise<UserInfo> {
  return apiClient.get("auth/me").json<UserInfo>();
}

export async function getMenuTreeApi(): Promise<MenuItem[]> {
  return apiClient.get("auth/menu-tree").json<MenuItem[]>();
}
