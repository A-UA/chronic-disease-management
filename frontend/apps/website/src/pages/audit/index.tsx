import { useState, useEffect } from "react";
import { Card, Table, Tag, App, Select, Space, Typography } from "antd";
import { FileSearchOutlined, ClockCircleOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { listAuditLogs, type AuditLogItem } from "@/api/audit";

const ACTION_COLORS: Record<string, string> = {
  login: "blue",
  register: "cyan",
  create: "green",
  update: "orange",
  delete: "red",
  upload: "purple",
  download: "geekblue",
};

export default function AuditLogsPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<AuditLogItem[]>([]);
  const [actionFilter, setActionFilter] = useState<string | undefined>();
  const [resourceFilter, setResourceFilter] = useState<string | undefined>();
  const { message } = App.useApp();

  const fetchData = async () => {
    setLoading(true);
    try {
      setData(
        await listAuditLogs({
          action: actionFilter,
          resourceType: resourceFilter,
          limit: 100,
        }),
      );
    } catch {
      void message.error("加载审计日志失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, [actionFilter, resourceFilter]);

  const columns: ColumnsType<AuditLogItem> = [
    {
      title: "时间",
      dataIndex: "createdAt",
      key: "createdAt",
      width: 180,
      render: (t: string) => (
        <Space>
          <ClockCircleOutlined style={{ color: "#999" }} />
          <Typography.Text>{new Date(t).toLocaleString("zh-CN")}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "用户",
      dataIndex: "userEmail",
      key: "userEmail",
      width: 200,
      ellipsis: true,
      render: (email: string | undefined) => email || "-",
    },
    {
      title: "操作",
      dataIndex: "action",
      key: "action",
      width: 120,
      render: (action: string) => <Tag color={ACTION_COLORS[action] || "default"}>{action}</Tag>,
    },
    {
      title: "资源类型",
      dataIndex: "resourceType",
      key: "resourceType",
      width: 140,
      render: (type: string) => <Tag>{type}</Tag>,
    },
    {
      title: "资源 ID",
      dataIndex: "resourceId",
      key: "resourceId",
      width: 140,
      ellipsis: true,
      render: (id: string | null) => id || "-",
    },
    {
      title: "IP 地址",
      dataIndex: "ipAddress",
      key: "ipAddress",
      width: 140,
      render: (ip: string | null) => ip || "-",
    },
    {
      title: "详情",
      dataIndex: "details",
      key: "details",
      ellipsis: true,
      render: (text: string | null) =>
        text ? <Typography.Text ellipsis={{ tooltip: text }}>{text}</Typography.Text> : "-",
    },
  ];

  return (
    <Card
      title={
        <Space>
          <FileSearchOutlined style={{ color: "#667eea" }} />
          <span>操作审计日志</span>
        </Space>
      }
      extra={
        <Space>
          <Select
            allowClear
            placeholder="操作类型"
            value={actionFilter}
            onChange={setActionFilter}
            style={{ width: 140 }}
            options={[
              { label: "登录", value: "login" },
              { label: "创建", value: "create" },
              { label: "更新", value: "update" },
              { label: "删除", value: "delete" },
              { label: "上传", value: "upload" },
            ]}
          />
          <Select
            allowClear
            placeholder="资源类型"
            value={resourceFilter}
            onChange={setResourceFilter}
            style={{ width: 140 }}
            options={[
              { label: "用户", value: "User" },
              { label: "患者", value: "PatientProfile" },
              { label: "文档", value: "Document" },
              { label: "知识库", value: "KnowledgeBase" },
              { label: "对话", value: "Conversation" },
            ]}
          />
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20, showTotal: (total) => `共 ${total} 条` }}
        size="middle"
      />
    </Card>
  );
}
