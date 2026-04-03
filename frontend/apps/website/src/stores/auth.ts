import { create } from "zustand";
import { loginApi, getMeApi, getMenuTreeApi } from "@/api/auth";
import { setToken, clearToken, setOrgId, getStoredToken } from "@/api/client";
import type { UserInfo, MenuItem } from "@/types/auth";

interface AuthState {
  token: string | null;
  user: UserInfo | null;
  menus: MenuItem[];
  permissions: string[];
  loading: boolean;

  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUserInfo: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: getStoredToken(),
  user: null,
  menus: [],
  permissions: [],
  loading: false,

  login: async (email, password) => {
    const res = await loginApi(email, password);
    setToken(res.access_token);
    set({ token: res.access_token });
    await get().fetchUserInfo();
  },

  logout: () => {
    clearToken();
    set({ token: null, user: null, menus: [], permissions: [] });
  },

  fetchUserInfo: async () => {
    set({ loading: true });
    try {
      const [user, menus] = await Promise.all([getMeApi(), getMenuTreeApi()]);
      if (user.org_id) {
        setOrgId(String(user.org_id));
      }
      set({
        user,
        menus,
        permissions: user.permissions ?? [],
        loading: false,
      });
    } catch {
      get().logout();
      set({ loading: false });
    }
  },
}));
