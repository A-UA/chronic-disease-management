import { useState, Suspense } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import PageLoading from "@/components/PageLoading";

export default function AdminLayout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <Sidebar collapsed={collapsed} onCollapse={setCollapsed} />

      <div className={`transition-all duration-300 ${collapsed ? "ml-16" : "ml-60"}`}>
        {/* 顶部栏 */}
        <header className="sticky top-0 z-20 h-14 bg-card/80 backdrop-blur-lg border-b border-border flex items-center px-6">
          <div className="flex-1" />
        </header>

        {/* 内容区 */}
        <main className="p-6">
          <Suspense fallback={<PageLoading />}>
            <Outlet />
          </Suspense>
        </main>

        {/* 底部 */}
        <footer className="text-center py-4 text-xs text-muted-foreground">
          © 2026 慢病管理系统
        </footer>
      </div>
    </div>
  );
}
