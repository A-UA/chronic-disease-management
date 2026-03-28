import { PlusOutlined } from '@ant-design/icons';
import {
  ModalForm,
  PageContainer,
  ProFormText,
  ProTable,
} from '@ant-design/pro-components';
import { listUsers, updateUserStatus, createUser } from '@/services/api/admin';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { Button, message, Popconfirm, Tag } from 'antd';
import { useRef } from 'react';

export default () => {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns[] = [
    {
      title: 'User Info',
      dataIndex: 'email',
      copyable: true,
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{record.name || 'Anonymous'}</div>
          <div style={{ fontSize: '12px', color: '#666' }}>{record.email}</div>
        </div>
      ),
    },
    {
      title: 'Tenants',
      dataIndex: 'org_count',
      sorter: true,
      render: (count) => <Tag color="blue">{count} Orgs</Tag>,
    },
    {
      title: 'Status',
      dataIndex: 'is_active',
      hideInSearch: true,
      render: (_, record) => (
        <Tag color={record.deleted_at ? 'error' : 'success'}>
          {record.deleted_at ? 'Inactive' : 'Active'}
        </Tag>
      ),
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      sorter: true,
    },
    {
      title: 'Operations',
      valueType: 'option',
      key: 'option',
      render: (text, record) => [
        <Popconfirm
          key="toggle"
          title={record.deleted_at ? 'Reactivate user?' : 'Disable user?'}
          onConfirm={async () => {
            await updateUserStatus(record.id, !!record.deleted_at);
            message.success('Status updated');
            actionRef.current?.reload();
          }}
        >
          <a style={{ color: record.deleted_at ? 'green' : 'red' }}>
            {record.deleted_at ? 'Activate' : 'Disable'}
          </a>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <PageContainer>
      <ProTable
        columns={columns}
        actionRef={actionRef}
        request={async (params) => {
          const data = await listUsers({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            search: params.email,
          });
          return { data, success: true, total: data.length };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        pagination={{ pageSize: 20 }}
        headerTitle="Global User Management"
        toolBarRender={() => [
          <ModalForm
            key="create"
            title="Register New User"
            trigger={
              <Button type="primary">
                <PlusOutlined /> New User
              </Button>
            }
            onFinish={async (values: any) => {
              await createUser(values);
              message.success('User registered successfully');
              actionRef.current?.reload();
              return true;
            }}
          >
            <ProFormText
              name="email"
              label="Email"
              placeholder="user@example.com"
              rules={[{ required: true, type: 'email' }]}
            />
            <ProFormText
              name="name"
              label="Full Name"
              placeholder="Enter name"
            />
            <ProFormText.Password
              name="password"
              label="Password"
              rules={[{ required: true, min: 6 }]}
            />
          </ModalForm>,
        ]}
      />
    </PageContainer>
  );
};
