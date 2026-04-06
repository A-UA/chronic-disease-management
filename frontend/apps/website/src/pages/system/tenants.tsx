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
  Popconfirm,
  Typography,
  Tooltip,
  Progress,
} from "antd";
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
  BankOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  listTenants,
  createTenant,
  updateTenant,
  deleteTenant,
  type TenantItem,
  type TenantCreateReq,
} from "@/api/system";

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  active: { color: "green", label: "活跃" },
  trial: { color: "blue", label: "试用" },
  suspended: { color: "red", label: "停用" },
  archived: { color: "default", label: "归档" },
};

const PLAN_MAP: Record<string, { color: string; label: string }> = {
  free: { color: "default", label: "免费版" },
  pro: { color: "blue", label: "专业版" },
  enterprise: { color: "purple", label: "企业版" },
};

export default function TenantsPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<TenantItem[]>([]);
  const [search, setSearch] = useState("");
  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<TenantItem | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();
  const { message } = App.useApp();

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      setData(await listTenants({ search: search || undefined, limit: 100 }));
    } catch {
      void message.error("加载租户列表失败");
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
    form.setFieldsValue({ plan_type: "free", status: "active", quota_tokens_limit: 1000000 });
    setModalOpen(true);
  };

  const openEdit = (record: TenantItem) => {
    setEditing(record);
    form.setFieldsValue(record);
    setModalOpen(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setSubmitting(true);
      if (editing) {
        await updateTenant(editing.id, values);
        void message.success("更新成功");
      } else {
        await createTenant(values as TenantCreateReq);
        void message.success("创建成功");
      }
      setModalOpen(false);
      void fetchData();
    } catch {
      /* validation error */
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteTenant(id);
      void message.success("删除成功");
      void fetchData();
    } catch {
      void message.error("删除失败，请检查是否存在关联组织");
    }
  };

  const columns: ColumnsType<TenantItem> = [
    {
      title: "租户",
      key: "name",
      render: (_, r) => (
        <Space>
          <BankOutlined style={{ color: "#667eea", fontSize: 16 }} />
          <div>
            <Typography.Text strong>{r.name}</Typography.Text>
            <br />
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {r.slug}
            </Typography.Text>
          </div>
        </Space>
      ),
    },
    {
      title: "套餐",
      dataIndex: "plan_type",
      width: 100,
      render: (v: string) => {
        const info = PLAN_MAP[v] || { color: "default", label: v };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
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
      title: "Token 配额",
      key: "quota",
      width: 200,
      render: (_, r) => {
        const pct =
          r.quota_tokens_limit > 0
            ? Math.round((r.quota_tokens_used / r.quota_tokens_limit) * 100)
            : 0;
        return (
          <Tooltip
            title={`${r.quota_tokens_used.toLocaleString()} / ${r.quota_tokens_limit.toLocaleString()}`}
          >
            <Progress percent={pct} size="small" status={pct > 90 ? "exception" : "active"} />
          </Tooltip>
        );
      },
    },
    {
      title: "组织数",
      dataIndex: "org_count",
      width: 80,
      render: (v: number) => <Tag>{v}</Tag>,
    },
    {
      title: "创建时间",
      dataIndex: "created_at",
      width: 170,
      render: (v: string) => new Date(v).toLocaleString("zh-CN"),
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
          <Popconfirm title="确定删除该租户？" onConfirm={() => void handleDelete(record.id)}>
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
          <BankOutlined style={{ color: "#667eea" }} />
          <span>租户管理</span>
        </Space>
      }
      extra={
        <Space>
          <Input
            placeholder="搜索租户..."
            prefix={<SearchOutlined />}
            allowClear
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ width: 200 }}
          />
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
            新建租户
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
        title={editing ? "编辑租户" : "新建租户"}
        open={modalOpen}
        onOk={() => void handleSubmit()}
        onCancel={() => setModalOpen(false)}
        confirmLoading={submitting}
        width={560}
        destroyOnClose
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="name"
            label="租户名称"
            rules={[{ required: true, message: "请输入租户名称" }]}
          >
            <Input placeholder="例如：XX 医院" />
          </Form.Item>
          <Form.Item
            name="slug"
            label="标识 (slug)"
            rules={[{ required: true, message: "请输入唯一标识" }]}
          >
            <Input placeholder="例如：xx-hospital" disabled={!!editing} />
          </Form.Item>
          <Space style={{ width: "100%" }} size="large">
            <Form.Item name="plan_type" label="套餐类型">
              <Select
                style={{ width: 140 }}
                options={[
                  { label: "免费版", value: "free" },
                  { label: "专业版", value: "pro" },
                  { label: "企业版", value: "enterprise" },
                ]}
              />
            </Form.Item>
            <Form.Item name="status" label="状态">
              <Select
                style={{ width: 140 }}
                options={[
                  { label: "活跃", value: "active" },
                  { label: "试用", value: "trial" },
                  { label: "停用", value: "suspended" },
                  { label: "归档", value: "archived" },
                ]}
              />
            </Form.Item>
          </Space>
          <Form.Item name="quota_tokens_limit" label="Token 配额">
            <InputNumber style={{ width: "100%" }} min={0} step={100000} />
          </Form.Item>
          <Space style={{ width: "100%" }} size="large">
            <Form.Item name="max_members" label="最大成员数">
              <InputNumber style={{ width: 140 }} min={0} />
            </Form.Item>
            <Form.Item name="max_patients" label="最大患者数">
              <InputNumber style={{ width: 140 }} min={0} />
            </Form.Item>
          </Space>
          <Form.Item name="contact_name" label="联系人">
            <Input placeholder="联系人姓名" />
          </Form.Item>
          <Space style={{ width: "100%" }} size="large">
            <Form.Item name="contact_phone" label="联系电话">
              <Input placeholder="联系电话" />
            </Form.Item>
            <Form.Item name="contact_email" label="联系邮箱">
              <Input placeholder="联系邮箱" />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Card>
  );
}
