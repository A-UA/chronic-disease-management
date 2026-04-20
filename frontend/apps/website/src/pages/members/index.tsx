import { useState, useEffect } from "react";
import { Card, Table, Button, App, Tag, Space, Popconfirm, Typography, Avatar } from "antd";
import { UserOutlined, DeleteOutlined, PlusOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { listMembers, removeMember, type OrgMember } from "@/api/members";
import { usePermission } from "@/hooks/usePermission";

const TYPE_MAP: Record<string, { color: string; label: string }> = {
  staff: { color: "blue", label: "员工" },
  patient: { color: "green", label: "患者" },
};

export default function MemberListPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<OrgMember[]>([]);
  const { message } = App.useApp();
  const { hasPermission } = usePermission();
  const canManage = hasPermission("org_member:manage");

  const fetchData = async () => {
    setLoading(true);
    try {
      setData(await listMembers());
    } catch {
      void message.error("加载成员列表失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, []);

  const handleRemove = async (userId: string) => {
    try {
      await removeMember(userId);
      void message.success("已移除");
      void fetchData();
    } catch {
      void message.error("移除失败");
    }
  };

  const columns: ColumnsType<OrgMember> = [
    {
      title: "用户",
      key: "user",
      render: (_, r) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: "#667eea" }} />
          <div>
            <Typography.Text strong>{r.name || r.email}</Typography.Text>
            <br />
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {r.email}
            </Typography.Text>
          </div>
        </Space>
      ),
    },
    {
      title: "类型",
      dataIndex: "userType",
      key: "userType",
      width: 100,
      render: (t: string) => {
        const info = TYPE_MAP[t] || { color: "default", label: t };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: "角色",
      key: "roles",
      render: (_, r) =>
        r.roles?.map((role) => (
          <Tag key={role.id} color="purple">
            {role.name}
          </Tag>
        )),
    },
    {
      title: "加入时间",
      dataIndex: "createdAt",
      key: "createdAt",
      width: 180,
      render: (t: string) => new Date(t).toLocaleString("zh-CN"),
    },
    ...(canManage
      ? [
          {
            title: "操作",
            key: "action",
            width: 100,
            render: (_: unknown, record: OrgMember) => (
              <Popconfirm
                title="确定移除该成员？"
                onConfirm={() => void handleRemove(record.userId)}
              >
                <Button type="link" danger icon={<DeleteOutlined />} size="small">
                  移除
                </Button>
              </Popconfirm>
            ),
          } as ColumnsType<OrgMember>[number],
        ]
      : []),
  ];

  return (
    <Card
      title="成员管理"
      extra={
        canManage && (
          <Button type="primary" icon={<PlusOutlined />}>
            邀请成员
          </Button>
        )
      }
    >
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
    </Card>
  );
}
