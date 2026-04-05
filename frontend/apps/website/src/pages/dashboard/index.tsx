import { Spin } from "antd";
import {
  TeamOutlined,
  UserOutlined,
  HeartOutlined,
  MessageOutlined,
  ThunderboltOutlined,
  CloudOutlined,
  WarningOutlined,
} from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { Line } from "@ant-design/charts";
import { getDashboardStats } from "@/api/dashboard";
import { useAuthStore } from "@/stores/auth";

const statCards = [
  {
    key: "total_organizations",
    title: "机构总数",
    icon: <TeamOutlined />,
    gradient: "gradient-card-1",
  },
  { key: "total_users", title: "用户总数", icon: <UserOutlined />, gradient: "gradient-card-2" },
  {
    key: "total_patients",
    title: "患者总数",
    icon: <HeartOutlined />,
    gradient: "gradient-card-3",
  },
  {
    key: "total_conversations",
    title: "对话总数",
    icon: <MessageOutlined />,
    gradient: "gradient-card-4",
  },
  {
    key: "active_users_24h",
    title: "24h 活跃",
    icon: <ThunderboltOutlined />,
    gradient: "gradient-card-7",
  },
  {
    key: "total_tokens_used",
    title: "Token 消耗",
    icon: <CloudOutlined />,
    gradient: "gradient-card-6",
  },
  {
    key: "recent_failed_docs",
    title: "失败文档",
    icon: <WarningOutlined />,
    gradient: "gradient-card-5",
  },
] as const;

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getDashboardStats,
  });

  if (isLoading || !data) {
    return <Spin size="large" className="!block !mx-auto !mt-24" />;
  }

  const lineConfig = {
    data: data.token_usage_trend ?? [],
    xField: "date",
    yField: "tokens",
    smooth: true,
    point: { size: 3, shape: "circle" },
    color: "#6366f1",
    area: { style: { fill: "l(270) 0:#6366f120 1:#6366f105" } },
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* 欢迎横幅 */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">欢迎回来，{user?.name || "用户"} 👋</h1>
        <p className="text-sm text-muted-foreground mt-1">这是您的系统概览</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-4 gap-4">
        {statCards.map((card, index) => (
          <div
            key={card.key}
            className={`${card.gradient} rounded-xl p-5 text-white shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300 animate-fade-in`}
            style={{ animationDelay: `${index * 0.05}s` }}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-white/80">{card.title}</span>
              <span className="text-xl text-white/60">{card.icon}</span>
            </div>
            <div className="text-3xl font-bold tracking-tight">
              {((data as any)[card.key] ?? 0).toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {/* 趋势图 */}
      <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-card-foreground">Token 用量趋势</h2>
            <p className="text-sm text-muted-foreground mt-0.5">近 7 天消耗统计</p>
          </div>
        </div>
        <Line {...lineConfig} />
      </div>
    </div>
  );
}
