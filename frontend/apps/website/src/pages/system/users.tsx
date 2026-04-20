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
  Avatar,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  UserOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
  listOrgs,
  listRoles,
  type UserItem,
  type UserCreateReq,
  type OrgItem,
  type RoleItem,
} from "@/api/system";

export default function UsersPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<UserItem[]>([]);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<UserItem | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // 组织和角色列表（用于创建表单的选择器）
  const [orgs, setOrgs] = useState<OrgItem[]>([]);
  const [roles, setRoles] = useState<RoleItem[]>([]);

  const [form] = Form.useForm();
  const { message } = App.useApp();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listUsers({ search: search || undefined, limit: 100 });
      setData(res.items);
    } catch {
      void message.error("加载用户列表失败");
    } finally {
      setLoading(false);
    }
  }, [search, message]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  // 加载组织和角色（用于新建用户表单）
  const loadOptions = useCallback(async () => {
    try {
      const [orgRes, roleList] = await Promise.all([listOrgs({ limit: 200 }), listRoles()]);
      setOrgs(orgRes.items);
      setRoles(roleList);
    } catch {
      /* silent */
    }
  }, []);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    void loadOptions();
    setModalOpen(true);
  };

  const openEdit = (record: UserItem) => {
    setEditing(record);
    form.setFieldsValue({ name: record.name, email: record.email });
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editing) {
        await updateUser(editing.id, { name: values.name, email: values.email });
        void message.success("更新成功");
      } else {
        await createUser(values as UserCreateReq);
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
      await deleteUser(id);
      void message.success("已禁用");
      void fetchData();
    } catch {
      void message.error("操作失败");
    }
  };

  const columns: ColumnsType<UserItem> = [
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
      title: "关联组织数",
      dataIndex: "orgCount",
      width: 110,
      render: (v: number) => <Tag color="blue">{v} 个</Tag>,
    },
    {
      title: "创建时间",
      dataIndex: "createdAt",
      width: 170,
      render: (v: string) => new Date(v).toLocaleString("zh-CN"),
    },
    {
      title: "操作",
      key: "action",
      width: 160,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确定禁用该用户？" onConfirm={() => void handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              禁用
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={
        <Space>
          <UserOutlined style={{ color: "#667eea" }} />
          <span>用户管理</span>
        </Space>
      }
      extra={
        <Space>
          <Input
            placeholder="搜索用户..."
            prefix={<SearchOutlined />}
            allowClear
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 200 }}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建用户
          </Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 15, showTotal: (total) => `共 ${total} 条` }}
        size="middle"
      />

      <Modal
        title={editing ? "编辑用户" : "新建用户"}
        open={modalOpen}
        onOk={() => void handleSubmit()}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="email"
            label="邮箱"
            rules={[
              { required: true, message: "请输入邮箱" },
              { type: "email", message: "邮箱格式不正确" },
            ]}
          >
            <Input placeholder="user@example.com" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="name" label="姓名">
            <Input placeholder="用户姓名" />
          </Form.Item>
          {!editing && (
            <>
              <Form.Item
                name="password"
                label="密码"
                rules={[{ required: true, message: "请输入密码", min: 6 }]}
              >
                <Input.Password placeholder="至少 6 位" />
              </Form.Item>
              <Form.Item name="orgId" label="所属组织">
                <Select
                  placeholder="默认绑定当前组织"
                  allowClear
                  showSearch
                  optionFilterProp="label"
                  options={orgs.map((o) => ({ label: `${o.name} (${o.code})`, value: o.id }))}
                />
              </Form.Item>
              <Form.Item name="roleIds" label="分配角色">
                <Select
                  mode="multiple"
                  placeholder="默认分配 staff 角色"
                  allowClear
                  optionFilterProp="label"
                  options={roles.map((r) => ({
                    label: `${r.name} (${r.code})`,
                    value: r.id,
                    disabled: r.isSystem,
                  }))}
                />
              </Form.Item>
            </>
          )}
        </Form>
      </Modal>
    </Card>
  );
}
