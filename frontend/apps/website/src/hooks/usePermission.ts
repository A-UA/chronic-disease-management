import { useAuthStore } from "@/stores/auth";
import { useCallback } from "react";

export function usePermission() {
  const permissions = useAuthStore((s) => s.permissions);

  const hasPermission = useCallback((code: string) => permissions.includes(code), [permissions]);

  return { hasPermission, permissions };
}
