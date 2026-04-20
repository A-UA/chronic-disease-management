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
  Tabs,
  Avatar,
  Empty,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  ApartmentOutlined,
  UserOutlined,
  TeamOutlined,
  UserAddOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  listOrgs,
  createOrg,
  updateOrg,
  deleteOrg,
  listOrgMembers,
  removeOrgMember,
  addOrgMember,
  listUsers,
  listRoles,
  type OrgItem,
  type OrgCreateReq,
  type OrgMemberItem,
  type UserItem,
  type RoleItem,
} from "@/api/system";

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  active: { color: "green", label: "活跃" },
  inactive: { color: "default", label: "停用" },
  archived: { color: "red", label: "归档" },
};

export default function OrgsPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<OrgItem[]>([]);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<OrgItem | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // 成员管理状态
  const [memberDrawer, setMemberDrawer] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<OrgItem | null>(null);
  const [members, setMembers] = useState<OrgMemberItem[]>([]);
  const [memberLoading, setMemberLoading] = useState(false);

  // 添加成员状态
  const [addMemberOpen, setAddMemberOpen] = useState(false);
  const [allUsers, setAllUsers] = useState<UserItem[]>([]);
  const [allRoles, setAllRoles] = useState<RoleItem[]>([]);
  const [addMemberForm] = Form.useForm();

  const [form] = Form.useForm();
  const { message } = App.useApp();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listOrgs({ search: search || undefined, limit: 200 });
      setData(res.items);
    } catch {
      void message.error("加载组织列表失败");
    } finally {
      setLoading(false);
    }
  }, [search, message]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ status: "active" });
    setModalOpen(true);
  };

  const openEdit = (record: OrgItem) => {
    setEditing(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editing) {
        await updateOrg(editing.id, values);
        void message.success("更新成功");
      } else {
        await createOrg(values as OrgCreateReq);
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
      await deleteOrg(id);
      void message.success("删除成功");
      void fetchData();
    } catch {
      void message.error("删除失败，请先移除组织下的成员");
    }
  };

  // ── 成员管理 ──
  const openMembers = async (org: OrgItem) => {
    setSelectedOrg(org);
    setMemberDrawer(true);
    setMemberLoading(true);
    try {
      setMembers(await listOrgMembers(org.id));
    } catch {
      void message.error("加载成员失败");
    } finally {
      setMemberLoading(false);
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!selectedOrg) return;
    try {
      await removeOrgMember(selectedOrg.id, userId);
      void message.success("已移除");
      setMembers(await listOrgMembers(selectedOrg.id));
    } catch {
      void message.error("移除失败");
    }
  };

  // ── 添加成员 ──
  const openAddMember = async () => {
    addMemberForm.resetFields();
    setAddMemberOpen(true);
    try {
      const [usersRes, rolesRes] = await Promise.all([listUsers({ limit: 200 }), listRoles()]);
      setAllUsers(usersRes.items);
      setAllRoles(rolesRes);
    } catch {
      /* silent */
    }
  };

  const handleAddMember = async () => {
    if (!selectedOrg) return;
    try {
      const values = await addMemberForm.validateFields();
      await addOrgMember(selectedOrg.id, {
        userId: values.userId,
        roleIds: values.roleIds,
        userType: values.userType || "staff",
      });
      void message.success("添加成功");
      setAddMemberOpen(false);
      setMembers(await listOrgMembers(selectedOrg.id));
    } catch {
      void message.error("添加失败");
    }
  };

  const memberColumns: ColumnsType<OrgMemberItem> = [
    {
      title: "用户",
      key: "user",
      render: (_, r) => (
        <Space>
          <Avatar icon={<UserOutlined />} size="small" style={{ backgroundColor: "#667eea" }} />
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
      width: 80,
      render: (t: string) => (
        <Tag color={t === "staff" ? "blue" : "green"}>{t === "staff" ? "员工" : "患者"}</Tag>
      ),
    },
    {
      title: "角色",
      key: "roles",
      render: (_, r) =>
        r.roles.map((role) => (
          <Tag key={role} color="purple">
            {role}
          </Tag>
        )),
    },
    {
      title: "操作",
      key: "action",
      width: 80,
      render: (_, r) => (
        <Popconfirm title="确定移除该成员？" onConfirm={() => void handleRemoveMember(r.userId)}>
          <Button type="link" size="small" danger icon={<DeleteOutlined />}>
            移除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const orgColumns: ColumnsType<OrgItem> = [
    {
      title: "组织",
      key: "name",
      render: (_, r) => (
        <Space>
          <ApartmentOutlined style={{ color: "#667eea", fontSize: 16 }} />
          <div>
            <Typography.Text strong>{r.name}</Typography.Text>
            <br />
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {r.code}
            </Typography.Text>
          </div>
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      width: 80,
      render: (v: string) => {
        const info = STATUS_MAP[v] || { color: "default", label: v };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: "描述",
      dataIndex: "description",
      ellipsis: true,
      render: (v: string | null) => v || "-",
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
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<TeamOutlined />}
            onClick={() => void openMembers(record)}
          >
            成员
          </Button>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确定删除该组织？" onConfirm={() => void handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Card
        title={
          <Space>
            <ApartmentOutlined style={{ color: "#667eea" }} />
            <span>组织管理</span>
          </Space>
        }
        extra={
          <Space>
            <Input
              placeholder="搜索组织..."
              prefix={<SearchOutlined />}
              allowClear
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ width: 200 }}
            />
            <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
              新建组织
            </Button>
          </Space>
        }
      >
        <Table
          columns={orgColumns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 15, showTotal: (total) => `共 ${total} 条` }}
          size="middle"
        />
      </Card>

      {/* 组织编辑 Modal */}
      <Modal
        title={editing ? "编辑组织" : "新建组织"}
        open={modalOpen}
        onOk={() => void handleSubmit()}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="组织名称"
            rules={[{ required: true, message: "请输入组织名称" }]}
          >
            <Input placeholder="例如：内科" />
          </Form.Item>
          <Form.Item
            name="code"
            label="组织编码"
            rules={[{ required: true, message: "请输入编码" }]}
          >
            <Input placeholder="例如：INTERNAL_MED" disabled={!!editing} />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="组织描述..." />
          </Form.Item>
        </Form>
      </Modal>

      {/* 成员管理 Modal */}
      <Modal
        title={
          <Space>
            <TeamOutlined style={{ color: "#667eea" }} />
            <span>{selectedOrg?.name} — 成员管理</span>
          </Space>
        }
        open={memberDrawer}
        onCancel={() => setMemberDrawer(false)}
        footer={null}
        width={700}
        destroyOnClose
      >
        <Tabs
          defaultActiveKey="list"
          tabBarExtraContent={
            <Button
              type="primary"
              size="small"
              icon={<UserAddOutlined />}
              onClick={() => void openAddMember()}
            >
              添加成员
            </Button>
          }
          items={[
            {
              key: "list",
              label: `成员列表 (${members.length})`,
              children:
                members.length > 0 ? (
                  <Table
                    columns={memberColumns}
                    dataSource={members}
                    rowKey="userId"
                    loading={memberLoading}
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <Empty description="该组织暂无成员" />
                ),
            },
          ]}
        />
      </Modal>

      {/* 添加成员 Modal */}
      <Modal
        title="添加成员到组织"
        open={addMemberOpen}
        onOk={() => void handleAddMember()}
        onCancel={() => setAddMemberOpen(false)}
        destroyOnClose
      >
        <Form form={addMemberForm} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="userId"
            label="选择用户"
            rules={[{ required: true, message: "请选择用户" }]}
          >
            <Select
              showSearch
              placeholder="搜索并选择用户..."
              optionFilterProp="label"
              options={allUsers.map((u) => ({
                label: `${u.name || u.email} (${u.email})`,
                value: u.id,
              }))}
            />
          </Form.Item>
          <Form.Item name="roleIds" label="分配角色">
            <Select
              mode="multiple"
              placeholder="选择角色..."
              optionFilterProp="label"
              options={allRoles.map((r) => ({
                label: `${r.name} (${r.code})`,
                value: r.id,
              }))}
            />
          </Form.Item>
          <Form.Item name="userType" label="用户类型" initialValue="staff">
            <Select
              options={[
                { label: "员工", value: "staff" },
                { label: "患者", value: "patient" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
