import React, { useState } from 'react';
import { Table, Button, Space, Card, Modal, Form, Input, message, Tabs } from 'antd';
import { PlusOutlined, DeleteOutlined, FileTextOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../../api/client';
import DocUpload from '../../components/rag/DocUpload';

const KBManagement: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [selectedKB, setSelectedKB] = useState<any>(null);
  const [isDocModalVisible, setIsDocModalVisible] = useState(false);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 获取知识库列表
  const { data: kbs, isLoading } = useQuery({
    queryKey: ['org-kbs'],
    queryFn: async () => {
      const response = await client.get('/kb');
      return response.data;
    },
  });

  // 创建知识库
  const createMutation = useMutation({
    mutationFn: async (values: any) => {
      return await client.post('/kb', values);
    },
    onSuccess: () => {
      message.success('知识库创建成功');
      setIsModalVisible(false);
      queryClient.invalidateQueries({ queryKey: ['org-kbs'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '创建失败');
    },
  });

  const columns = [
    { title: '名称', dataIndex: 'name', key: 'name' },
    { title: '描述', dataIndex: 'description', key: 'description' },
    { title: '文档数量', dataIndex: 'document_count', key: 'document_count' },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (date: string) => new Date(date).toLocaleString() },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="middle">
          <Button 
            icon={<FileTextOutlined />} 
            onClick={() => {
              setSelectedKB(record);
              setIsDocModalVisible(true);
            }}
          >
            管理文档
          </Button>
          <Button icon={<DeleteOutlined />} danger>删除</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">知识库管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setIsModalVisible(true)}>
          新建知识库
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={kbs}
          loading={isLoading}
          rowKey="id"
        />
      </Card>

      {/* 新建知识库 Modal */}
      <Modal
        title="新建知识库"
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={createMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={(values) => createMutation.mutate(values)}>
          <Form.Item name="name" label="知识库名称" rules={[{ required: true }]}>
            <Input placeholder="例如：慢病指南" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="简要说明知识库用途" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 文档管理 Modal */}
      <Modal
        title={`知识库文档管理: ${selectedKB?.name}`}
        open={isDocModalVisible}
        onCancel={() => setIsDocModalVisible(false)}
        footer={null}
        width={800}
      >
        <DocUpload 
          kbId={selectedKB?.id} 
          onSuccess={() => queryClient.invalidateQueries({ queryKey: ['org-kbs'] })} 
        />
      </Modal>
    </div>
  );
};

export default KBManagement;
