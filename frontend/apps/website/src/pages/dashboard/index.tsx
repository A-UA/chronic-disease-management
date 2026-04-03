import { Card, Col, Row, Statistic, Spin, Typography } from "antd";
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

const { Title } = Typography;

const statCards = [
  { key: "total_organizations", title: "机构总数", icon: <TeamOutlined />, color: "#1677ff" },
  { key: "total_users", title: "用户总数", icon: <UserOutlined />, color: "#52c41a" },
  { key: "total_patients", title: "患者总数", icon: <HeartOutlined />, color: "#eb2f96" },
  { key: "total_conversations", title: "对话总数", icon: <MessageOutlined />, color: "#722ed1" },
  { key: "active_users_24h", title: "24h活跃", icon: <ThunderboltOutlined />, color: "#fa8c16" },
  { key: "total_tokens_used", title: "Token消耗", icon: <CloudOutlined />, color: "#13c2c2" },
  { key: "recent_failed_docs", title: "失败文档", icon: <WarningOutlined />, color: "#f5222d" },
] as const;

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: getDashboardStats,
  });

  if (isLoading || !data) {
    return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  }

  const lineConfig = {
    data: data.token_usage_trend ?? [],
    xField: "date",
    yField: "tokens",
    smooth: true,
    point: { size: 3 },
    color: "#1677ff",
  };

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>控制台</Title>
      <Row gutter={[16, 16]}>
        {statCards.map((card) => (
          <Col xs={24} sm={12} md={8} lg={6} key={card.key}>
            <Card hoverable>
              <Statistic
                title={card.title}
                value={(data as any)[card.key] ?? 0}
                prefix={card.icon}
                styles={{ content: { color: card.color } }}
              />
            </Card>
          </Col>
        ))}
      </Row>
      <Card title="Token 用量趋势（近7天）" style={{ marginTop: 24 }}>
        <Line {...lineConfig} />
      </Card>
    </div>
  );
}
