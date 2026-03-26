import React, { useState } from 'react';
import { Table, Button, Space, Card, Tag, Modal, Form, Input, Switch, message } from 'antd';
import { PlusOutlined, EditOutlined, EyeOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import client from '../../api/client';

const OrgManagement: React.FC = () => {
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [editingOrg, setEditingOrg] = useState<any>(null);
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 获取组织列表
  const { data: orgs, isLoading } = useQuery({
    queryKey: ['admin-orgs'],
    queryFn: async () => {
      const response = await client.get('/admin/organizations');
      return response.data;
    },
  });

  // 创建或更新组织
  const mutation = useMutation({
    mutationFn: async (values: any) => {
      if (editingOrg) {
        return await client.patch(`/admin/organizations/${editingOrg.id}`, values);
      }
      return await client.post('/admin/organizations', values);
    },
    onSuccess: () => {
      message.success(`${editingOrg ? '更新' : '创建'}成功`);
      setIsModalVisible(false);
      queryClient.invalidateQueries({ queryKey: ['admin-orgs'] });
    },
    onError: (error: any) => {
      message.error(error.response?.data?.detail || '操作失败');
    },
  });

  const showModal = (org?: any) => {
    setEditingOrg(org || null);
    if (org) {
      form.setFieldsValue(org);
    } else {
      form.resetFields();
    }
    setIsModalVisible(true);
  };

  const columns = [
    { title: '机构名称', dataIndex: 'name', key: 'name' },
    { title: '唯一标识', dataIndex: 'slug', key: 'slug' },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>{active ? '启用' : '禁用'}</Tag>
      ),
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at', render: (date: string) => new Date(date).toLocaleString() },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="middle">
          <Button icon={<EditOutlined />} onClick={() => showModal(record)}>编辑</Button>
          <Button icon={<EyeOutlined />}>详情</Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">机构管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => showModal()}>
          新增机构
        </Button>
      </div>

      <Card>
        <Table
          columns={columns}
          dataSource={orgs}
          loading={isLoading}
          rowKey="id"
        />
      </Card>

      <Modal
        title={editingOrg ? '编辑机构' : '新增机构'}
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={mutation.isPending}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(values) => mutation.mutate(values)}
          initialValues={{ is_active: true }}
        >
          <Form.Item
            name="name"
            label="机构名称"
            rules={[{ required: true, message: '请输入机构名称' }]}
          >
            <Input placeholder="例如：南方医院" />
          </Form.Item>
          
          <Form.Item
            name="slug"
            label="唯一标识 (Slug)"
            rules={[{ required: true, message: '请输入唯一标识' }]}
          >
            <Input placeholder="例如：nanfang-hospital" disabled={!!editingOrg} />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea placeholder="机构描述信息" />
          </Form.Item>

          <Form.Item
            name="is_active"
            label="启用状态"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default OrgManagement;
