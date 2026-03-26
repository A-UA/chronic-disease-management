import React, { useState } from 'react';
import { Table, Card, Drawer, Descriptions, Tag, Space, Button } from 'antd';
import { EyeOutlined, MessageOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import client from '../../api/client';
import ChatPane from '../../components/chat/ChatPane';

const PatientWorkbench: React.FC = () => {
  const [selectedPatient, setSelectedPatient] = useState<any>(null);
  const [chatDrawerVisible, setChatDrawerVisible] = useState(false);

  const { data: patients, isLoading } = useQuery({
    queryKey: ['biz-patients'],
    queryFn: async () => {
      const response = await client.get('/biz/patients');
      return response.data;
    },
  });

  const columns = [
    { title: '姓名', dataIndex: 'full_name', key: 'full_name' },
    { title: '性别', dataIndex: 'gender', key: 'gender', render: (g: string) => g === 'male' ? '男' : '女' },
    { title: '年龄', dataIndex: 'age', key: 'age' },
    { 
      title: '健康标签', 
      dataIndex: 'tags', 
      key: 'tags', 
      render: (tags: string[]) => (
        <>
          {tags?.map(tag => <Tag key={tag} color="blue">{tag}</Tag>)}
        </>
      ) 
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : 'orange'}>{status === 'active' ? '跟进中' : '待处理'}</Tag>
      )
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Space size="middle">
          <Button icon={<EyeOutlined />}>档案</Button>
          <Button 
            type="primary" 
            ghost 
            icon={<MessageOutlined />} 
            onClick={() => {
              setSelectedPatient(record);
              setChatDrawerVisible(true);
            }}
          >
            AI 咨询
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <h2 className="text-xl font-bold mb-6">患者管理工作台</h2>
      <Card>
        <Table
          columns={columns}
          dataSource={patients}
          loading={isLoading}
          rowKey="id"
        />
      </Card>

      <Drawer
        title={`AI 辅助咨询 - ${selectedPatient?.full_name}`}
        width={600}
        onClose={() => setChatDrawerVisible(false)}
        open={chatDrawerVisible}
        bodyStyle={{ padding: 0 }}
      >
        <div className="p-4 bg-blue-50 border-b border-blue-100">
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="患者 ID">{selectedPatient?.id}</Descriptions.Item>
            <Descriptions.Item label="当前知识库">默认医学库</Descriptions.Item>
          </Descriptions>
        </div>
        
        {/* 这里需要传入 kbId，由于后端通常有默认库或关联库，这里演示传入一个固定 ID 或由后端自动处理 */}
        <ChatPane patientId={selectedPatient?.id} kbId="default" />
      </Drawer>
    </div>
  );
};

export default PatientWorkbench;
