import ky from "ky";

const TOKEN_KEY = "cdm_token";
const ORG_KEY = "cdm_org_id";

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
        const orgId = localStorage.getItem(ORG_KEY);
        if (orgId) {
          request.headers.set("X-Organization-ID", orgId);
        }
      },
    ],
    afterResponse: [
      async (_request, _options, response) => {
        if (response.status === 401) {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(ORG_KEY);
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
  localStorage.removeItem(ORG_KEY);
}

export function setOrgId(orgId: string) {
  localStorage.setItem(ORG_KEY, orgId);
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
