import { useState, useEffect, useCallback } from "react";
import {
  Card,
  Table,
  Button,
  App,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Popconfirm,
  Typography,
  Tooltip,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SafetyCertificateOutlined,
  LockOutlined,
  TeamOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  listRoles,
  createRole,
  updateRole,
  deleteRole,
  listPermissions,
  type RoleItem,
  type RoleCreateReq,
  type PermissionItem,
} from "@/api/system";

export default function RolesPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<RoleItem[]>([]);
  const [permissions, setPermissions] = useState<PermissionItem[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<RoleItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();
  const { message } = App.useApp();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [roles, perms] = await Promise.all([listRoles(), listPermissions()]);
      setData(roles);
      setPermissions(perms);
    } catch {
      void message.error("加载数据失败");
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    setModalOpen(true);
  };

  const openEdit = (record: RoleItem) => {
    setEditing(record);
    form.setFieldsValue({
      name: record.name,
      code: record.code,
      description: record.description,
      parent_role_id: record.parent_role_id,
      permission_ids: record.permissions.map((p) => p.id),
    });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editing) {
        await updateRole(editing.id, {
          name: values.name,
          description: values.description,
          permission_ids: values.permission_ids,
        });
        void message.success("更新成功");
      } else {
        await createRole(values as RoleCreateReq);
        void message.success("创建成功");
      }
      setModalOpen(false);
      void fetchData();
    } catch {
      /* validation */
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteRole(id);
      void message.success("删除成功");
      void fetchData();
    } catch {
      void message.error("删除失败，请先解绑该角色下的用户");
    }
  };

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
      ellipsis: true,
      render: (text: string | null) => text || "-",
    },
    {
      title: "权限",
      key: "permissions",
      width: 350,
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
      title: "用户数",
      key: "user_count",
      width: 90,
      align: "center",
      render: (_, r) => (
        <Tag icon={<TeamOutlined />} color={r.user_count ? "blue" : "default"}>
          {r.user_count ?? 0}
        </Tag>
      ),
    },
    {
      title: "类型",
      key: "type",
      width: 100,
      render: (_, r) =>
        r.is_system ? <Tag color="orange">系统</Tag> : <Tag color="blue">自定义</Tag>,
    },
    {
      title: "操作",
      key: "action",
      width: 130,
      render: (_, record) =>
        record.is_system ? (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            不可操作
          </Typography.Text>
        ) : (
          <Space>
            <Button
              type="link"
              size="small"
              icon={<EditOutlined />}
              onClick={() => openEdit(record)}
            >
              编辑
            </Button>
            <Popconfirm title="确定删除该角色？" onConfirm={() => void handleDelete(record.id)}>
              <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                删除
              </Button>
            </Popconfirm>
          </Space>
        ),
    },
  ];

  // 用于父角色选择器（排除当前编辑的角色本身）
  const parentRoleOptions = data
    .filter((r) => !editing || r.id !== editing.id)
    .map((r) => ({ label: `${r.name} (${r.code})`, value: r.id }));

  return (
    <Card
      title={
        <Space>
          <SafetyCertificateOutlined style={{ color: "#667eea" }} />
          <span>角色管理</span>
        </Space>
      }
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建角色
        </Button>
      }
    >
      <Table columns={columns} dataSource={data} rowKey="id" loading={loading} pagination={false} />

      <Modal
        title={editing ? "编辑角色" : "新建角色"}
        open={modalOpen}
        onOk={() => void handleSubmit()}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="角色名称"
            rules={[{ required: true, message: "请输入角色名称" }]}
          >
            <Input placeholder="例如：审计员" />
          </Form.Item>
          {!editing && (
            <Form.Item
              name="code"
              label="角色编码"
              rules={[{ required: true, message: "请输入编码" }]}
            >
              <Input placeholder="例如：auditor" />
            </Form.Item>
          )}
          <Form.Item name="parent_role_id" label="继承角色">
            <Select
              allowClear
              placeholder="无（不继承）"
              options={parentRoleOptions}
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="角色描述..." />
          </Form.Item>
          <Form.Item
            name="permission_ids"
            label="权限"
            rules={[{ required: true, message: "请选择权限" }]}
          >
            <Select
              mode="multiple"
              placeholder="选择权限..."
              options={permissions.map((p) => ({ label: `${p.name} (${p.code})`, value: p.id }))}
              optionFilterProp="label"
            />
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  );
}
