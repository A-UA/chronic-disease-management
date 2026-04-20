import { useState, useEffect } from "react";
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  App,
  Space,
  Tag,
  Popconfirm,
  Typography,
  Statistic,
  Row,
  Col,
} from "antd";
import {
  PlusOutlined,
  DeleteOutlined,
  DatabaseOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  listKBs,
  createKB,
  deleteKB,
  type KnowledgeBase,
  type KBCreateRequest,
} from "@/api/knowledge";

const { TextArea } = Input;

export default function KBListPage() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<KnowledgeBase[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm<KBCreateRequest>();
  const { message } = App.useApp();

  const fetchData = async () => {
    setLoading(true);
    try {
      const list = await listKBs();
      setData(list);
    } catch {
      void message.error("加载知识库失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, []);

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await createKB(values);
      void message.success("知识库创建成功");
      setModalOpen(false);
      form.resetFields();
      void fetchData();
    } catch {
      void message.error("创建失败");
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteKB(id);
      void message.success("已删除");
      void fetchData();
    } catch {
      void message.error("删除失败");
    }
  };

  const columns: ColumnsType<KnowledgeBase> = [
    {
      title: "知识库名称",
      dataIndex: "name",
      key: "name",
      render: (text: string) => (
        <Space>
          <DatabaseOutlined style={{ color: "#667eea" }} />
          <Typography.Text strong>{text}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "描述",
      dataIndex: "description",
      key: "description",
      ellipsis: true,
      render: (text: string | null) =>
        text || <Typography.Text type="secondary">-</Typography.Text>,
    },
    {
      title: "文档数",
      dataIndex: "documentCount",
      key: "documentCount",
      width: 100,
      align: "center",
      render: (count: number) => <Tag color="blue">{count}</Tag>,
    },
    {
      title: "切块数",
      dataIndex: "chunkCount",
      key: "chunkCount",
      width: 100,
      align: "center",
      render: (count: number) => <Tag color="green">{count}</Tag>,
    },
    {
      title: "创建时间",
      dataIndex: "createdAt",
      key: "createdAt",
      width: 180,
      render: (t: string) => new Date(t).toLocaleString("zh-CN"),
    },
    {
      title: "操作",
      key: "action",
      width: 100,
      render: (_, record) => (
        <Popconfirm title="确定删除此知识库？" onConfirm={() => void handleDelete(record.id)}>
          <Button type="link" danger icon={<DeleteOutlined />} size="small">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  // 统计
  const totalDocs = data.reduce((s, kb) => s + (kb.documentCount || 0), 0);
  const totalChunks = data.reduce((s, kb) => s + (kb.chunkCount || 0), 0);

  return (
    <>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="知识库总数"
              value={data.length}
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: "#667eea" }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="文档总数"
              value={totalDocs}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: "#52c41a" }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic title="切块总数" value={totalChunks} valueStyle={{ color: "#fa8c16" }} />
          </Card>
        </Col>
      </Row>

      <Card
        title="知识库列表"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            新建知识库
          </Button>
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

      <Modal
        title="新建知识库"
        open={modalOpen}
        onOk={() => void handleCreate()}
        onCancel={() => setModalOpen(false)}
        okText="创建"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: "请输入名称" }]}>
            <Input placeholder="例如：高血压临床指南" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <TextArea rows={3} placeholder="知识库用途描述（可选）" />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
}
