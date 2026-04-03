export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserInfo {
  id: string;
  email: string;
  name: string | null;
  org_id: string | null;
  permissions: string[];
}

export interface MenuItem {
  id: string;
  name: string;
  code: string;
  menu_type: "directory" | "page" | "link";
  path: string | null;
  icon: string | null;
  permission_code: string | null;
  sort: number;
  is_visible: boolean;
  is_enabled: boolean;
  meta: Record<string, unknown> | null;
  children: MenuItem[];
}
