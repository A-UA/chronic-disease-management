import type { RouteObject } from "react-router-dom";
import { lazy, type ReactNode } from "react";

export interface RouteModule {
  index: ReactNode;
  children?: RouteObject[];
}

const DashboardPage = lazy(() => import("@/pages/dashboard/index"));
const PatientListPage = lazy(() => import("@/pages/patients/index"));
const PatientDetailPage = lazy(() => import("@/pages/patients/[id]"));

// 知识库管理
const KBListPage = lazy(() => import("@/pages/knowledge/list"));
const KBDocumentsPage = lazy(() => import("@/pages/knowledge/documents"));

// AI 问答
const AIChatPage = lazy(() => import("@/pages/chat/index"));

// 系统管理
const SysTenantsPage = lazy(() => import("@/pages/system/tenants"));
const SysOrgsPage = lazy(() => import("@/pages/system/orgs"));
const SysUsersPage = lazy(() => import("@/pages/system/users"));
const SysRolesPage = lazy(() => import("@/pages/system/roles"));
const SysMenusPage = lazy(() => import("@/pages/system/menus"));
const SysAuditPage = lazy(() => import("@/pages/system/audit"));

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
  "kb-list": {
    index: <KBListPage />,
  },
  "kb-documents": {
    index: <KBDocumentsPage />,
  },
  "ai-chat": {
    index: <AIChatPage />,
  },
  // ── 系统管理子模块 ──
  "sys-tenants": {
    index: <SysTenantsPage />,
  },
  "sys-orgs": {
    index: <SysOrgsPage />,
  },
  "sys-users": {
    index: <SysUsersPage />,
  },
  "sys-roles": {
    index: <SysRolesPage />,
  },
  "sys-menus": {
    index: <SysMenusPage />,
  },
  "sys-audit": {
    index: <SysAuditPage />,
  },
};
