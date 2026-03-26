import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// 这里从自动生成的 types.ts 中解构出相关的 User 接口。为了通用，这里先使用 any 并在具体调用时类型化。
interface AuthState {
  user: any | null;
  token: string | null;
  setAuth: (user: any, token: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      setAuth: (user, token) => {
        localStorage.setItem('auth_token', token);
        set({ user, token });
      },
      logout: () => {
        localStorage.removeItem('auth_token');
        set({ user: null, token: null });
      },
    }),
    {
      name: 'auth-storage', // 持久化到 localStorage 的名称
    }
  )
);
