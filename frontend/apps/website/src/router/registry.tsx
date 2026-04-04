import type { RouteObject } from "react-router-dom";
import { lazy, type ReactNode } from "react";

export interface RouteModule {
  index: ReactNode;
  children?: RouteObject[];
}

const DashboardPage = lazy(() => import("@/pages/dashboard/index"));
const PatientListPage = lazy(() => import("@/pages/patients/index"));
const PatientDetailPage = lazy(() => import("@/pages/patients/[id]"));

// F6: 知识库管理
const KBListPage = lazy(() => import("@/pages/knowledge/list"));
const KBDocumentsPage = lazy(() => import("@/pages/knowledge/documents"));

// F7: 成员管理 + 角色权限
const MemberListPage = lazy(() => import("@/pages/members/index"));
const RoleListPage = lazy(() => import("@/pages/roles/index"));

// F8: AI 问答
const AIChatPage = lazy(() => import("@/pages/chat/index"));

// F9: 操作审计
const AuditLogsPage = lazy(() => import("@/pages/audit/index"));

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
  "member-mgmt": {
    index: <MemberListPage />,
  },
  "role-mgmt": {
    index: <RoleListPage />,
  },
  "audit-logs": {
    index: <AuditLogsPage />,
  },
};
