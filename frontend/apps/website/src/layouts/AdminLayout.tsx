import { Suspense } from "react";
import { Outlet, useNavigate, useLocation } from "react-router-dom";
import { ProLayout } from "@ant-design/pro-components";
import { LogoutOutlined, UserOutlined } from "@ant-design/icons";
import { Dropdown, message } from "antd";
import * as Icons from "@ant-design/icons";
import { useAuthStore } from "@/stores/auth";
import PageLoading from "@/components/PageLoading";
import type { MenuItem } from "@/types/auth";

function menusToRoutes(menus: MenuItem[]): any[] {
  return menus
    .filter((m) => m.is_visible)
    .map((menu) => {
      const IconComp = menu.icon ? (Icons as Record<string, any>)[menu.icon] : undefined;
      return {
        path: menu.path ?? "/",
        name: menu.name,
        icon: IconComp ? <IconComp /> : undefined,
        children: menu.children?.length ? menusToRoutes(menu.children) : undefined,
      };
    });
}

export default function AdminLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, menus, logout } = useAuthStore();

  const handleLogout = () => {
    logout();
    message.success("已退出登录");
    void navigate("/login");
  };

  return (
    <ProLayout
      title="慢病管理系统"
      layout="mix"
      fixSiderbar
      route={{ routes: menusToRoutes(menus) }}
      location={{ pathname: location.pathname }}
      menu={{ type: "sub" }}
      menuItemRender={(item, dom) => (
        <div onClick={() => item.path && navigate(item.path)}>{dom}</div>
      )}
      avatarProps={{
        icon: <UserOutlined />,
        title: user?.name || user?.email || "用户",
        render: (_props: any, dom: any) => (
          <Dropdown
            menu={{
              items: [
                {
                  key: "logout",
                  icon: <LogoutOutlined />,
                  label: "退出登录",
                  onClick: handleLogout,
                },
              ],
            }}
          >
            {dom}
          </Dropdown>
        ),
      }}
      footerRender={() => (
        <div style={{ textAlign: "center", padding: 16, color: "#999" }}>© 2026 慢病管理系统</div>
      )}
    >
      <Suspense fallback={<PageLoading />}>
        <Outlet />
      </Suspense>
    </ProLayout>
  );
}
