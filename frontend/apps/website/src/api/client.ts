import ky from "ky";

const TOKEN_KEY = "cdm_token";

export const apiClient = ky.create({
  prefixUrl: "/api/v1",
  timeout: 30000,
  hooks: {
    beforeRequest: [
      (request) => {
        const token = localStorage.getItem(TOKEN_KEY);
        if (token) {
          request.headers.set("Authorization", `Bearer ${token}`);
        }
        // 注意：不再注入 X-Organization-ID
        // org_id 已内嵌在 JWT 中，由后端从 token 解析
      },
    ],
    afterResponse: [
      async (_request, _options, response) => {
        if (response.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          window.location.href = "/login";
        }
      },
    ],
  },
});

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
