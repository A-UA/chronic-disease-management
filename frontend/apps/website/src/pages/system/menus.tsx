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
  InputNumber,
  Switch,
  Popconfirm,
  Typography,
} from "antd";
import { PlusOutlined, EditOutlined, DeleteOutlined, MenuOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  listMenus,
  createMenu,
  updateMenu,
  deleteMenu,
  listPermissions,
  type MenuItemData,
  type MenuCreateReq,
  type PermissionItem,
} from "@/api/system";

const TYPE_MAP: Record<string, { color: string; label: string }> = {
  directory: { color: "purple", label: "目录" },
  page: { color: "blue", label: "页面" },
  link: { color: "cyan", label: "链接" },
};

/** 递归扁平化菜单树，用于父级选择器 */
function flattenMenus(menus: MenuItemData[], depth = 0): { label: string; value: string }[] {
  const result: { label: string; value: string }[] = [];
  for (const m of menus) {
    result.push({ label: `${"—".repeat(depth)} ${m.name}`, value: m.id });
    if (m.children?.length) {
      result.push(...flattenMenus(m.children, depth + 1));
    }
  }
  return result;
}

export default function MenusPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<MenuItemData[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<MenuItemData | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();
  const { message } = App.useApp();
  const [permissions, setPermissions] = useState<PermissionItem[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [menus, perms] = await Promise.all([listMenus(), listPermissions()]);
      setData(menus);
      setPermissions(perms);
    } catch {
      void message.error("加载菜单列表失败");
    } finally {
      setLoading(false);
    }
  }, [message]);

  useEffect(() => {
    void fetchData();
  }, [fetchData]);

  const parentOptions = flattenMenus(data);

  const openCreate = () => {
    setEditing(null);
    form.resetFields();
    form.setFieldsValue({ menu_type: "page", sort: 0, is_visible: true, is_enabled: true });
    setModalOpen(true);
  };

  const openEdit = (record: MenuItemData) => {
    setEditing(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editing) {
        await updateMenu(editing.id, values);
        void message.success("更新成功");
      } else {
        await createMenu(values as MenuCreateReq);
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
      await deleteMenu(id);
      void message.success("删除成功");
      void fetchData();
    } catch {
      void message.error("删除失败");
    }
  };

  const columns: ColumnsType<MenuItemData> = [
    {
      title: "菜单名称",
      dataIndex: "name",
      key: "name",
      render: (name: string, r) => (
        <Space>
          <Typography.Text strong>{name}</Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 11 }}>
            ({r.code})
          </Typography.Text>
        </Space>
      ),
    },
    {
      title: "类型",
      dataIndex: "menu_type",
      width: 80,
      render: (v: string) => {
        const info = TYPE_MAP[v] || { color: "default", label: v };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: "路径",
      dataIndex: "path",
      width: 180,
      ellipsis: true,
      render: (v: string | null) => (v ? <Typography.Text code>{v}</Typography.Text> : "-"),
    },
    {
      title: "图标",
      dataIndex: "icon",
      width: 120,
      render: (v: string | null) => v || "-",
    },
    {
      title: "权限码",
      dataIndex: "permission_code",
      width: 140,
      render: (v: string | null) => (v ? <Tag color="geekblue">{v}</Tag> : "-"),
    },
    {
      title: "排序",
      dataIndex: "sort",
      width: 60,
      align: "center",
    },
    {
      title: "状态",
      key: "status",
      width: 80,
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          {r.is_visible ? <Tag color="green">可见</Tag> : <Tag>隐藏</Tag>}
        </Space>
      ),
    },
    {
      title: "操作",
      key: "action",
      width: 130,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="删除将级联删除子菜单，确定？"
            onConfirm={() => void handleDelete(record.id)}
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
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
          <MenuOutlined style={{ color: "#667eea" }} />
          <span>菜单管理</span>
        </Space>
      }
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建菜单
        </Button>
      }
    >
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={false}
        expandable={{ childrenColumnName: "children" }}
        size="middle"
      />

      <Modal
        title={editing ? "编辑菜单" : "新建菜单"}
        open={modalOpen}
        onOk={() => void handleSubmit()}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        width={560}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="parent_id" label="父级菜单">
            <Select
              allowClear
              placeholder="无（一级菜单）"
              options={parentOptions}
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item
            name="name"
            label="菜单名称"
            rules={[{ required: true, message: "请输入菜单名称" }]}
          >
            <Input placeholder="例如：患者列表" />
          </Form.Item>
          <Form.Item
            name="code"
            label="唯一编码"
            rules={[{ required: true, message: "请输入编码" }]}
          >
            <Input placeholder="例如：patient-list" disabled={!!editing} />
          </Form.Item>
          <Space style={{ width: "100%" }} size="large">
            <Form.Item name="menu_type" label="类型">
              <Select
                style={{ width: 140 }}
                options={[
                  { label: "目录", value: "directory" },
                  { label: "页面", value: "page" },
                  { label: "链接", value: "link" },
                ]}
              />
            </Form.Item>
            <Form.Item name="sort" label="排序">
              <InputNumber style={{ width: 100 }} min={0} />
            </Form.Item>
          </Space>
          <Form.Item name="path" label="路由路径">
            <Input placeholder="例如：/patients/list" />
          </Form.Item>
          <Form.Item name="icon" label="图标名称">
            <Input placeholder="例如：TeamOutlined" />
          </Form.Item>
          <Form.Item name="permission_code" label="权限编码">
            <Select
              allowClear
              placeholder="无权限限制"
              showSearch
              optionFilterProp="label"
              options={permissions.map((p) => ({ label: `${p.name} (${p.code})`, value: p.code }))}
            />
          </Form.Item>
          <Space size="large">
            <Form.Item name="is_visible" label="侧边栏可见" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Form.Item name="is_enabled" label="启用" valuePropName="checked">
              <Switch />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Card>
  );
}
