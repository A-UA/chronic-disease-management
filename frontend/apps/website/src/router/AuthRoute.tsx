import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import PageLoading from "@/components/PageLoading";

export default function AuthRoute() {
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const loading = useAuthStore((s) => s.loading);
  const fetchUserInfo = useAuthStore((s) => s.fetchUserInfo);
  const location = useLocation();

  useEffect(() => {
    if (token && !user && !loading) {
      void fetchUserInfo();
    }
  }, [token, user, loading, fetchUserInfo]);

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (loading || !user) {
    return <PageLoading />;
  }

  return <Outlet />;
}
