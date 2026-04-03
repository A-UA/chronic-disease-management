import type { RouteObject } from "react-router-dom";
import type { MenuItem } from "@/types/auth";
import { routeRegistry } from "./registry";
import { Outlet } from "react-router-dom";

function stripLeadingSlash(path: string | null): string {
  if (!path) return "";
  return path.startsWith("/") ? path.slice(1) : path;
}

/**
 * 将子菜单 path 转为相对于父菜单 path 的路径
 * 例如 parent="/patients", child="/patients/metrics" → "metrics"
 * 例如 parent="/patients", child="/patients" → ""（index 路由）
 */
function relativePath(parentPath: string, childPath: string): string {
  const parent = stripLeadingSlash(parentPath);
  const child = stripLeadingSlash(childPath);
  if (child === parent) return "";
  if (child.startsWith(parent + "/")) return child.slice(parent.length + 1);
  return child;
}

export function generateRoutes(menus: MenuItem[], parentPath?: string): RouteObject[] {
  return menus
    .filter((menu) => menu.menu_type !== "link" && menu.is_visible)
    .flatMap((menu): RouteObject[] => {
      const mod = routeRegistry[menu.code];
      const menuPath = menu.path ?? "";

      if (menu.menu_type === "directory") {
        const dirPath = stripLeadingSlash(menuPath);
        const childRoutes = generateRoutes(menu.children ?? [], menuPath);
        return [
          {
            path: parentPath ? relativePath(parentPath, menuPath) : dirPath,
            element: <Outlet />,
            handle: { permission: menu.permission_code, menuCode: menu.code },
            children: childRoutes,
          } satisfies RouteObject,
        ];
      }

      // page 类型
      const pagePath = parentPath
        ? relativePath(parentPath, menuPath)
        : stripLeadingSlash(menuPath);
      const isIndex = pagePath === "";

      const route: RouteObject = isIndex
        ? {
            index: true,
            element: mod?.index ?? null,
            handle: { permission: menu.permission_code, menuCode: menu.code },
          }
        : {
            path: pagePath,
            handle: { permission: menu.permission_code, menuCode: menu.code },
            children: [{ index: true, element: mod?.index ?? null }, ...(mod?.children ?? [])],
          };

      // 非 index 路由也需要挂载 mod.children（如 :id 子路由）
      if (isIndex && mod?.children?.length) {
        return [route, ...mod.children];
      }

      return [route];
    });
}
