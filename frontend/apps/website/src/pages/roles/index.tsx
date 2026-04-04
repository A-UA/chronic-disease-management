import { useState, useEffect } from "react";
import { Card, Table, Tag, App, Space, Typography, Tooltip } from "antd";
import { SafetyCertificateOutlined, LockOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { listRoles, type RoleItem } from "@/api/members";

export default function RoleListPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<RoleItem[]>([]);
  const { message } = App.useApp();

  useEffect(() => {
    setLoading(true);
    void listRoles()
      .then((list) => setData(list))
      .catch(() => void message.error("加载角色列表失败"))
      .finally(() => setLoading(false));
  }, []);

  const columns: ColumnsType<RoleItem> = [
    {
      title: "角色",
      key: "name",
      render: (_, r) => (
        <Space>
          <SafetyCertificateOutlined style={{ color: r.is_system ? "#fa8c16" : "#667eea" }} />
          <div>
            <Typography.Text strong>{r.name}</Typography.Text>
            {r.is_system && (
              <Tooltip title="系统预置角色，不可修改">
                <LockOutlined style={{ marginLeft: 6, color: "#fa8c16", fontSize: 12 }} />
              </Tooltip>
            )}
            <br />
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {r.code}
            </Typography.Text>
          </div>
        </Space>
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      render: (text: string | null) => text || "-",
    },
    {
      title: "权限",
      key: "permissions",
      width: 400,
      render: (_, r) => (
        <Space size={[4, 4]} wrap>
          {r.permissions?.map((p) => (
            <Tag key={p.id} color="geekblue" style={{ fontSize: 11 }}>
              {p.name}
            </Tag>
          ))}
          {(!r.permissions || r.permissions.length === 0) && (
            <Typography.Text type="secondary">继承上级角色</Typography.Text>
          )}
        </Space>
      ),
    },
    {
      title: "类型",
      key: "type",
      width: 100,
      render: (_, r) =>
        r.is_system ? <Tag color="orange">系统</Tag> : <Tag color="blue">自定义</Tag>,
    },
  ];

  return (
    <Card title="角色权限">
      <Table columns={columns} dataSource={data} rowKey="id" loading={loading} pagination={false} />
    </Card>
  );
}
