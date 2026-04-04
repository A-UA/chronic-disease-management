import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Button, Card, Form, Input, Typography, App, List, Avatar } from "antd";
import { LockOutlined, MailOutlined, BankOutlined, ArrowLeftOutlined } from "@ant-design/icons";
import { useAuthStore } from "@/stores/auth";
import type { OrgBrief } from "@/types/auth";

const { Title, Text } = Typography;

export default function LoginPage() {
  const [loading, setLoading] = useState(false);
  const [selectingOrg, setSelectingOrg] = useState(false);
  const token = useAuthStore((s) => s.token);
  const user = useAuthStore((s) => s.user);
  const login = useAuthStore((s) => s.login);
  const selectOrg = useAuthStore((s) => s.selectOrg);
  const pendingOrgs = useAuthStore((s) => s.pendingOrgs);
  const clearPendingOrgs = useAuthStore((s) => s.clearPendingOrgs);
  const { message } = App.useApp();

  // 已登录：声明式重定向
  if (token && user) {
    return <Navigate to="/" replace />;
  }

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.email, values.password);
      // 如果是单部门，login 会自动完成，触发 <Navigate>
      // 如果是多部门，pendingOrgs 会被填充
      if (!useAuthStore.getState().pendingOrgs) {
        void message.success("登录成功");
      }
    } catch {
      void message.error("用户名或密码错误");
    } finally {
      setLoading(false);
    }
  };

  const onSelectOrg = async (org: OrgBrief) => {
    setSelectingOrg(true);
    try {
      await selectOrg(org.id);
      void message.success(`已进入「${org.name}」`);
    } catch {
      void message.error("选择部门失败，请重试");
    } finally {
      setSelectingOrg(false);
    }
  };

  const onBack = () => {
    clearPendingOrgs();
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
      }}
    >
      <Card
        style={{
          width: 420,
          borderRadius: 12,
          boxShadow: "0 8px 32px rgba(0,0,0,0.15)",
        }}
      >
        {pendingOrgs ? (
          /* ── 部门选择界面 ── */
          <>
            <div style={{ display: "flex", alignItems: "center", marginBottom: 16 }}>
              <Button
                type="text"
                icon={<ArrowLeftOutlined />}
                onClick={onBack}
                style={{ marginRight: 8 }}
              />
              <Title level={4} style={{ margin: 0 }}>
                选择部门
              </Title>
            </div>
            <Text type="secondary" style={{ display: "block", marginBottom: 16 }}>
              您属于多个部门，请选择要进入的部门：
            </Text>
            <List
              dataSource={pendingOrgs}
              loading={selectingOrg}
              renderItem={(org) => (
                <List.Item
                  key={org.id}
                  style={{
                    cursor: "pointer",
                    borderRadius: 8,
                    padding: "12px 16px",
                    transition: "background-color 0.2s",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLElement).style.backgroundColor = "#f0f5ff";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLElement).style.backgroundColor = "transparent";
                  }}
                  onClick={() => void onSelectOrg(org)}
                >
                  <List.Item.Meta
                    avatar={
                      <Avatar icon={<BankOutlined />} style={{ backgroundColor: "#667eea" }} />
                    }
                    title={org.name}
                    description={org.tenant_name ?? "默认工作区"}
                  />
                </List.Item>
              )}
            />
          </>
        ) : (
          /* ── 登录表单 ── */
          <>
            <Title level={3} style={{ textAlign: "center", marginBottom: 32 }}>
              慢病管理系统
            </Title>
            <Form onFinish={onFinish} size="large">
              <Form.Item name="email" rules={[{ required: true, message: "请输入邮箱" }]}>
                <Input prefix={<MailOutlined />} placeholder="邮箱" />
              </Form.Item>
              <Form.Item name="password" rules={[{ required: true, message: "请输入密码" }]}>
                <Input.Password prefix={<LockOutlined />} placeholder="密码" />
              </Form.Item>
              <Form.Item>
                <Button type="primary" htmlType="submit" loading={loading} block>
                  登录
                </Button>
              </Form.Item>
            </Form>
          </>
        )}
      </Card>
    </div>
  );
}
