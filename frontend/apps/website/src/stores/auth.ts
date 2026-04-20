import { create } from "zustand";
import { loginApi, getMeApi, getMenuTreeApi, selectOrgApi, switchOrgApi } from "@/api/auth";
import { setToken, clearToken, getStoredToken } from "@/api/client";
import type { UserInfo, MenuItem, OrgBrief } from "@/types/auth";

interface AuthState {
  /** JWT token（不透明字符串，不要解析） */
  token: string | null;
  user: UserInfo | null;
  menus: MenuItem[];
  permissions: string[];
  loading: boolean;

  /** 当前所在部门信息 */
  currentOrg: OrgBrief | null;

  /** 多部门登录时的临时状态 */
  pendingOrgs: OrgBrief[] | null;
  selectionToken: string | null;

  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  fetchUserInfo: () => Promise<void>;

  /** 多部门登录时选择部门 */
  selectOrg: (orgId: string) => Promise<void>;

  /** 已登录后切换部门 */
  switchOrg: (orgId: string) => Promise<void>;

  /** 清除多部门选择状态 */
  clearPendingOrgs: () => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  token: getStoredToken(),
  user: null,
  menus: [],
  permissions: [],
  loading: false,
  currentOrg: null,
  pendingOrgs: null,
  selectionToken: null,

  login: async (email, password) => {
    const res = await loginApi(email, password);

    if (res.requireOrgSelection) {
      // 多部门 → 暂存部门列表，等用户选择
      set({
        pendingOrgs: res.organizations,
        selectionToken: res.selectionToken,
        token: null,
      });
      return;
    }

    // 单部门 → 直接登录
    setToken(res.accessToken);
    set({
      token: res.accessToken,
      currentOrg: res.organization,
      pendingOrgs: null,
      selectionToken: null,
    });
    await get().fetchUserInfo();
  },

  selectOrg: async (orgId: string) => {
    const { selectionToken } = get();
    if (!selectionToken) {
      throw new Error("没有 selectionToken，无法选择部门");
    }

    const res = await selectOrgApi(orgId, selectionToken);
    setToken(res.accessToken);
    set({
      token: res.accessToken,
      currentOrg: res.organization,
      pendingOrgs: null,
      selectionToken: null,
    });
    await get().fetchUserInfo();
  },

  switchOrg: async (orgId: string) => {
    const res = await switchOrgApi(orgId);
    setToken(res.accessToken);
    set({
      token: res.accessToken,
      currentOrg: res.organization,
    });
    await get().fetchUserInfo();
  },

  clearPendingOrgs: () => {
    set({ pendingOrgs: null, selectionToken: null });
  },

  logout: () => {
    clearToken();
    set({
      token: null,
      user: null,
      menus: [],
      permissions: [],
      currentOrg: null,
      pendingOrgs: null,
      selectionToken: null,
    });
  },

  fetchUserInfo: async () => {
    set({ loading: true });
    try {
      const [user, menus] = await Promise.all([getMeApi(), getMenuTreeApi()]);
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
