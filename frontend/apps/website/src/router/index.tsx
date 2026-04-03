import { useMemo } from "react";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router-dom";
import { useAuthStore } from "@/stores/auth";
import { generateRoutes } from "./generateRoutes";
import AuthRoute from "./AuthRoute";
import AdminLayout from "@/layouts/AdminLayout";
import LoginPage from "@/pages/login/index";
import NotFound from "@/pages/404";

export default function AppRouter() {
  const menus = useAuthStore((s) => s.menus);

  const router = useMemo(() => {
    const dynamicRoutes = generateRoutes(menus);

    return createBrowserRouter([
      { path: "/login", element: <LoginPage /> },
      {
        element: <AuthRoute />,
        children: [
          {
            element: <AdminLayout />,
            children: [
              { index: true, element: <Navigate to="/dashboard" replace /> },
              ...dynamicRoutes,
              { path: "*", element: <NotFound /> },
            ],
          },
        ],
      },
    ]);
  }, [menus]);

  return <RouterProvider router={router} />;
}
