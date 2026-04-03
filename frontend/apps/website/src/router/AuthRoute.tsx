import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import PageLoading from "@/components/PageLoading";

export default function AuthRoute() {
  const { user, loading, fetchUserInfo, hydrate } = useAuthStore();
  const location = useLocation();
  const currentToken = useAuthStore((s) => s.token);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (currentToken && !user && !loading) {
      void fetchUserInfo();
    }
  }, [currentToken, user, loading, fetchUserInfo]);

  if (!currentToken) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (loading || !user) {
    return <PageLoading />;
  }

  return <Outlet />;
}
