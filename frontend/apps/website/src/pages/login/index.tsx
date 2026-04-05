import { useState } from "react";
import { Navigate } from "react-router-dom";
import { Form, Input, App } from "antd";
import { LockOutlined, MailOutlined, BankOutlined, ArrowLeftOutlined } from "@ant-design/icons";
import { useAuthStore } from "@/stores/auth";
import type { OrgBrief } from "@/types/auth";

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

  if (token && user) {
    return <Navigate to="/" replace />;
  }

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.email, values.password);
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

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-[oklch(0.30_0.15_268)] via-[oklch(0.25_0.18_280)] to-[oklch(0.20_0.12_300)]">
      {/* 装饰光圈 */}
      <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full bg-[oklch(0.45_0.20_268/0.15)] blur-3xl animate-float" />
      <div
        className="absolute bottom-[-15%] right-[-5%] w-[400px] h-[400px] rounded-full bg-[oklch(0.40_0.18_310/0.12)] blur-3xl animate-float"
        style={{ animationDelay: "3s" }}
      />
      <div
        className="absolute top-[30%] right-[15%] w-[250px] h-[250px] rounded-full bg-[oklch(0.50_0.15_200/0.10)] blur-2xl animate-float"
        style={{ animationDelay: "1.5s" }}
      />

      {/* 登录卡片 */}
      <div className="relative z-10 w-full max-w-[420px] mx-4 animate-fade-in">
        <div className="rounded-2xl border border-white/10 bg-white/[0.07] backdrop-blur-2xl shadow-2xl p-8">
          {pendingOrgs ? (
            /* ── 部门选择 ── */
            <>
              <button
                type="button"
                onClick={() => clearPendingOrgs()}
                className="flex items-center gap-2 text-white/60 hover:text-white transition-colors mb-6 bg-transparent border-0 cursor-pointer text-sm"
              >
                <ArrowLeftOutlined /> 返回登录
              </button>
              <h2 className="text-xl font-semibold text-white mb-2">选择部门</h2>
              <p className="text-sm text-white/50 mb-6">您属于多个部门，请选择要进入的部门</p>
              <div className="space-y-2">
                {pendingOrgs.map((org) => (
                  <button
                    key={org.id}
                    type="button"
                    disabled={selectingOrg}
                    onClick={() => void onSelectOrg(org)}
                    className="w-full flex items-center gap-4 p-4 rounded-xl bg-white/[0.06] border border-white/10 hover:bg-white/[0.12] hover:border-white/20 transition-all duration-200 cursor-pointer text-left disabled:opacity-50"
                  >
                    <div className="w-10 h-10 rounded-lg gradient-primary flex items-center justify-center shrink-0">
                      <BankOutlined className="text-white text-lg" />
                    </div>
                    <div className="min-w-0">
                      <div className="text-white font-medium truncate">{org.name}</div>
                      <div className="text-white/40 text-xs truncate">
                        {org.tenant_name ?? "默认工作区"}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </>
          ) : (
            /* ── 登录表单 ── */
            <>
              <div className="text-center mb-8">
                <div className="w-14 h-14 rounded-2xl gradient-primary flex items-center justify-center mx-auto mb-4 shadow-lg shadow-[oklch(0.55_0.22_268/0.3)]">
                  <span className="text-white font-bold text-xl">慢</span>
                </div>
                <h1 className="text-2xl font-bold text-white mb-1">慢病管理系统</h1>
                <p className="text-sm text-white/40">Chronic Disease Management</p>
              </div>

              <Form onFinish={onFinish} size="large" layout="vertical">
                <Form.Item name="email" rules={[{ required: true, message: "请输入邮箱" }]}>
                  <Input
                    prefix={<MailOutlined className="text-white/30" />}
                    placeholder="邮箱"
                    className="!bg-white/[0.06] !border-white/10 !text-white placeholder:!text-white/30 hover:!border-white/20 focus:!border-[oklch(0.55_0.22_268)] !rounded-xl !h-12"
                  />
                </Form.Item>
                <Form.Item name="password" rules={[{ required: true, message: "请输入密码" }]}>
                  <Input.Password
                    prefix={<LockOutlined className="text-white/30" />}
                    placeholder="密码"
                    className="!bg-white/[0.06] !border-white/10 !text-white placeholder:!text-white/30 hover:!border-white/20 focus:!border-[oklch(0.55_0.22_268)] !rounded-xl !h-12"
                  />
                </Form.Item>
                <Form.Item className="!mb-0 !mt-2">
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full h-12 rounded-xl gradient-primary text-white font-semibold text-base border-0 cursor-pointer hover:opacity-90 active:scale-[0.98] transition-all duration-200 shadow-lg shadow-[oklch(0.55_0.22_268/0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? "登录中..." : "登 录"}
                  </button>
                </Form.Item>
              </Form>
            </>
          )}
        </div>

        <p className="text-center text-white/20 text-xs mt-6">© 2026 慢病管理系统</p>
      </div>
    </div>
  );
}
