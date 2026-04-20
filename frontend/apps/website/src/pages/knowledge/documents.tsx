import { useState, useEffect } from "react";
import { Card, Table, Button, Upload, App, Tag, Select, Space, Popconfirm, Typography } from "antd";
import {
  UploadOutlined,
  DeleteOutlined,
  ReloadOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import {
  listKBs,
  listDocuments,
  deleteDocument,
  type KnowledgeBase,
  type KBDocument,
} from "@/api/knowledge";

const STATUS_MAP: Record<string, { color: string; label: string }> = {
  pending: { color: "default", label: "等待中" },
  processing: { color: "processing", label: "处理中" },
  completed: { color: "success", label: "已完成" },
  failed: { color: "error", label: "失败" },
};

export default function KBDocumentsPage() {
  const [kbList, setKBList] = useState<KnowledgeBase[]>([]);
  const [selectedKB, setSelectedKB] = useState<string | null>(null);
  const [docs, setDocs] = useState<KBDocument[]>([]);
  const [loading, setLoading] = useState(false);
  const { message } = App.useApp();

  // 加载知识库列表
  useEffect(() => {
    void listKBs()
      .then((list) => {
        setKBList(list);
        if (list.length > 0 && !selectedKB) {
          setSelectedKB(list[0].id);
        }
      })
      .catch(() => void message.error("加载知识库列表失败"));
  }, []);

  // 加载文档列表
  const fetchDocs = async () => {
    if (!selectedKB) return;
    setLoading(true);
    try {
      const list = await listDocuments(selectedKB);
      setDocs(list);
    } catch {
      void message.error("加载文档失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchDocs();
  }, [selectedKB]);

  const handleDelete = async (id: string) => {
    try {
      await deleteDocument(id);
      void message.success("已删除");
      void fetchDocs();
    } catch {
      void message.error("删除失败");
    }
  };

  const columns: ColumnsType<KBDocument> = [
    {
      title: "文件名",
      dataIndex: "fileName",
      key: "fileName",
      render: (text: string) => (
        <Space>
          <FileTextOutlined style={{ color: "#667eea" }} />
          <Typography.Text>{text}</Typography.Text>
        </Space>
      ),
    },
    {
      title: "状态",
      dataIndex: "status",
      key: "status",
      width: 120,
      render: (status: string) => {
        const info = STATUS_MAP[status] || { color: "default", label: status };
        return <Tag color={info.color}>{info.label}</Tag>;
      },
    },
    {
      title: "切块数",
      dataIndex: "chunkCount",
      key: "chunkCount",
      width: 100,
      align: "center",
    },
    {
      title: "失败原因",
      dataIndex: "failedReason",
      key: "failedReason",
      ellipsis: true,
      render: (text: string | null) =>
        text ? (
          <Typography.Text type="danger" ellipsis={{ tooltip: text }}>
            {text}
          </Typography.Text>
        ) : (
          "-"
        ),
    },
    {
      title: "上传时间",
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
        <Popconfirm title="确定删除？" onConfirm={() => void handleDelete(record.id)}>
          <Button type="link" danger icon={<DeleteOutlined />} size="small">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const uploadProps = {
    name: "file",
    action: `/api/v1/documents/kb/${selectedKB ?? ""}/documents`,
    headers: {
      Authorization: `Bearer ${localStorage.getItem("cdm_token") ?? ""}`,
    },
    accept: ".pdf,.txt,.doc,.docx,.md",
    showUploadList: false,
    onChange(info: { file: { status?: string; name?: string } }) {
      if (info.file.status === "done") {
        void message.success(`${info.file.name} 上传成功`);
        void fetchDocs();
      } else if (info.file.status === "error") {
        void message.error(`${info.file.name} 上传失败`);
      }
    },
  };

  return (
    <Card
      title="文档管理"
      extra={
        <Space>
          <Select
            placeholder="选择知识库"
            value={selectedKB}
            onChange={(v) => setSelectedKB(v)}
            style={{ width: 200 }}
            options={kbList.map((kb) => ({ label: kb.name, value: kb.id }))}
          />
          <Upload {...uploadProps}>
            <Button type="primary" icon={<UploadOutlined />} disabled={!selectedKB}>
              上传文档
            </Button>
          </Upload>
          <Button icon={<ReloadOutlined />} onClick={() => void fetchDocs()}>
            刷新
          </Button>
        </Space>
      }
    >
      <Table
        columns={columns}
        dataSource={docs}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 10 }}
      />
    </Card>
  );
}
