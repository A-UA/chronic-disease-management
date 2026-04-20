import { useState, useMemo } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Tooltip, Dropdown } from "antd";
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
  SwapOutlined,
  UserOutlined,
  RightOutlined,
} from "@ant-design/icons";
import * as Icons from "@ant-design/icons";
import { useAuthStore } from "@/stores/auth";
import type { MenuItem } from "@/types/auth";

interface SidebarProps {
  collapsed: boolean;
  onCollapse: (v: boolean) => void;
}

export default function Sidebar({ collapsed, onCollapse }: SidebarProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, menus, currentOrg, logout } = useAuthStore();
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());

  /* 自动展开当前活动菜单的父级 */
  const activeMenuPath = useMemo(() => {
    const find = (items: MenuItem[], parents: string[] = []): string[] | null => {
      for (const item of items) {
        if (!item.isVisible) continue;
        const cur = [...parents, item.code];
        if (item.path && location.pathname.startsWith(item.path)) return cur;
        if (item.children?.length) {
          const found = find(item.children, cur);
          if (found) return found;
        }
      }
      return null;
    };
    return find(menus) ?? [];
  }, [menus, location.pathname]);

  useMemo(() => {
    if (activeMenuPath.length > 1) {
      setExpandedKeys((prev) => {
        const next = new Set(prev);
        activeMenuPath.slice(0, -1).forEach((code) => next.add(code));
        return next;
      });
    }
  }, [activeMenuPath]);

  const toggleExpand = (code: string) => {
    setExpandedKeys((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  };

  const getIcon = (iconName?: string | null) => {
    if (!iconName) return null;
    const Comp = (Icons as Record<string, any>)[iconName];
    return Comp ? <Comp className="text-[16px]" /> : null;
  };

  const handleLogout = () => {
    logout();
    void navigate("/login");
  };

  const renderItem = (item: MenuItem, depth = 0) => {
    if (!item.isVisible) return null;
    const hasChildren = item.children?.some((c) => c.isVisible);
    const isActive = !hasChildren && item.path ? location.pathname.startsWith(item.path) : false;
    const isExpanded = expandedKeys.has(item.code);

    return (
      <div key={item.code}>
        <Tooltip title={collapsed ? item.name : ""} placement="right">
          <button
            type="button"
            onClick={() => {
              if (hasChildren) toggleExpand(item.code);
              else if (item.path) void navigate(item.path);
            }}
            className={[
              "relative w-full flex items-center gap-3 rounded-lg transition-all duration-200",
              "text-sm cursor-pointer border-0 outline-none bg-transparent",
              collapsed ? "justify-center mx-1 p-2.5" : "mx-2 px-3 py-2.5",
              depth > 0 && !collapsed ? "ml-9 mr-2 !w-auto" : "",
              isActive
                ? "bg-sidebar-accent text-sidebar-primary font-semibold"
                : "text-sidebar-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground",
            ].join(" ")}
          >
            {isActive && !collapsed && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-sidebar-primary rounded-r-full" />
            )}
            {depth === 0 && getIcon(item.icon)}
            {!collapsed && (
              <>
                <span className="flex-1 text-left truncate">{item.name}</span>
                {hasChildren && (
                  <RightOutlined
                    className={`text-[10px] transition-transform duration-200 ${isExpanded ? "rotate-90" : ""}`}
                  />
                )}
              </>
            )}
          </button>
        </Tooltip>

        {hasChildren && !collapsed && (
          <div
            className={`overflow-hidden transition-all duration-200 ${
              isExpanded ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
            }`}
          >
            {item.children?.map((child) => renderItem(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  return (
    <aside
      className={`fixed left-0 top-0 h-screen flex flex-col z-30 bg-sidebar border-r border-sidebar-border transition-all duration-300 ease-in-out ${
        collapsed ? "w-16" : "w-60"
      }`}
    >
      {/* Logo */}
      <div
        className={`flex items-center h-14 border-b border-sidebar-border shrink-0 ${
          collapsed ? "justify-center px-2" : "px-4 gap-3"
        }`}
      >
        <div className="w-8 h-8 rounded-lg gradient-primary flex items-center justify-center shrink-0">
          <span className="text-white font-bold text-sm">慢</span>
        </div>
        {!collapsed && (
          <span className="font-semibold text-sidebar-foreground text-[15px] truncate">
            慢病管理
          </span>
        )}
      </div>

      {/* 菜单 */}
      <nav className="flex-1 overflow-y-auto py-3 space-y-0.5 scrollbar-thin">
        {menus.filter((m) => m.isVisible).map((item) => renderItem(item))}
      </nav>

      {/* 折叠按钮 */}
      <button
        type="button"
        onClick={() => onCollapse(!collapsed)}
        className="mx-2 mb-2 p-2 rounded-lg text-sidebar-muted-foreground hover:bg-sidebar-accent/50 hover:text-sidebar-foreground transition-colors cursor-pointer border-0 outline-none bg-transparent"
      >
        {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
      </button>

      {/* 用户区 */}
      <div
        className={`border-t border-sidebar-border p-2 ${collapsed ? "flex justify-center" : ""}`}
      >
        <Dropdown
          menu={{
            items: [
              ...(currentOrg
                ? [{ key: "org", label: currentOrg.name, icon: <SwapOutlined />, disabled: true }]
                : []),
              { type: "divider" as const },
              {
                key: "logout",
                label: "退出登录",
                icon: <LogoutOutlined />,
                danger: true,
                onClick: handleLogout,
              },
            ],
          }}
          trigger={["click"]}
          placement="topRight"
        >
          <button
            type="button"
            className={`w-full flex items-center gap-3 p-2 rounded-lg cursor-pointer hover:bg-sidebar-accent/50 transition-colors border-0 outline-none bg-transparent ${
              collapsed ? "justify-center" : ""
            }`}
          >
            <div className="w-8 h-8 rounded-full bg-sidebar-accent flex items-center justify-center shrink-0">
              <UserOutlined className="text-sidebar-primary text-sm" />
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0 text-left">
                <div className="text-sm font-medium text-sidebar-foreground truncate">
                  {user?.name || "用户"}
                </div>
                <div className="text-xs text-sidebar-muted-foreground truncate">{user?.email}</div>
              </div>
            )}
          </button>
        </Dropdown>
      </div>
    </aside>
  );
}
