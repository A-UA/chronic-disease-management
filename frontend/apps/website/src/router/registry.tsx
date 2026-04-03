import type { RouteObject } from "react-router-dom";
import { lazy, type ReactNode } from "react";

export interface RouteModule {
  index: ReactNode;
  children?: RouteObject[];
}

const DashboardPage = lazy(() => import("@/pages/dashboard/index"));
const PatientListPage = lazy(() => import("@/pages/patients/index"));
const PatientDetailPage = lazy(() => import("@/pages/patients/[id]"));

export const routeRegistry: Record<string, RouteModule> = {
  dashboard: {
    index: <DashboardPage />,
    children: [],
  },
  "patient-list": {
    index: <PatientListPage />,
    children: [
      {
        path: ":id",
        element: <PatientDetailPage />,
        handle: { breadcrumb: "患者详情" },
      },
    ],
  },
};
