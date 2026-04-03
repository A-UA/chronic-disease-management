import type { RouteObject } from "react-router-dom";
import type { MenuItem } from "@/types/auth";
import { routeRegistry } from "./registry";

function stripLeadingSlash(path: string | null): string {
  if (!path) return "";
  return path.startsWith("/") ? path.slice(1) : path;
}

export function generateRoutes(menus: MenuItem[]): RouteObject[] {
  return menus
    .filter((menu) => menu.menu_type !== "link" && menu.is_visible)
    .map((menu) => {
      const mod = routeRegistry[menu.code];

      if (menu.menu_type === "directory") {
        return {
          path: stripLeadingSlash(menu.path),
          handle: { permission: menu.permission_code, menuCode: menu.code },
          children: [...generateRoutes(menu.children ?? []), ...(mod?.children ?? [])],
        } satisfies RouteObject;
      }

      return {
        path: stripLeadingSlash(menu.path),
        handle: { permission: menu.permission_code, menuCode: menu.code },
        children: [{ index: true, element: mod?.index ?? null }, ...(mod?.children ?? [])],
      } satisfies RouteObject;
    });
}
