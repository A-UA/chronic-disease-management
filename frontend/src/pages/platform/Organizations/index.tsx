import { PlusOutlined } from '@ant-design/icons';
import {
  ModalForm,
  PageContainer,
  ProFormDigit,
  ProFormSelect,
  ProFormText,
  ProTable,
} from '@ant-design/pro-components';
import { Button, message, Popconfirm, Progress, Space, Tag } from 'antd';
import {
  listOrganizations,
  createOrganization,
  updateOrganization,
  deleteOrganization,
} from '@/services/api/admin';
import type { ProColumns, ActionType } from '@ant-design/pro-components';
import { useRef } from 'react';

export default () => {
  const actionRef = useRef<ActionType>();

  const columns: ProColumns[] = [
    {
      title: 'Organization Name',
      dataIndex: 'name',
      copyable: true,
      formItemProps: {
        rules: [{ required: true, message: 'Organization name is required' }],
      },
    },
    {
      title: 'Plan',
      dataIndex: 'plan_type',
      filters: true,
      valueEnum: {
        free: { text: 'Free', status: 'Default' },
        pro: { text: 'Pro', status: 'Success' },
        enterprise: { text: 'Enterprise', status: 'Processing' },
      },
      render: (_, record) => {
        const color =
          record.plan_type === 'enterprise' ? 'purple' : record.plan_type === 'pro' ? 'blue' : 'default';
        return <Tag color={color}>{record.plan_type.toUpperCase()}</Tag>;
      },
    },
    {
      title: 'Token Usage',
      dataIndex: 'quota_tokens_used',
      hideInSearch: true,
      render: (_, record) => (
        <div style={{ width: 150 }}>
          <Progress
            percent={record.quota_usage_percent}
            size="small"
            status={record.quota_usage_percent > 90 ? 'exception' : 'active'}
          />
          <small>
            {record.quota_tokens_used.toLocaleString()} / {record.quota_tokens_limit.toLocaleString()}
          </small>
        </div>
      ),
    },
    {
      title: 'Created At',
      dataIndex: 'created_at',
      valueType: 'dateTime',
      sorter: true,
      hideInForm: true,
    },
    {
      title: 'Operations',
      valueType: 'option',
      key: 'option',
      render: (text, record, _, action) => [
        <ModalForm
          key="edit"
          title="Edit Organization"
          trigger={<a>Edit</a>}
          initialValues={record}
          onFinish={async (values) => {
            await updateOrganization(record.id, values);
            message.success('Updated successfully');
            actionRef.current?.reload();
            return true;
          }}
        >
          <ProFormText name="name" label="Name" />
          <ProFormSelect
            name="plan_type"
            label="Plan"
            options={[
              { label: 'Free', value: 'free' },
              { label: 'Pro', value: 'pro' },
              { label: 'Enterprise', value: 'enterprise' },
            ]}
          />
          <ProFormDigit name="quota_tokens_limit" label="Token Quota" />
        </ModalForm>,
        <Popconfirm
          key="delete"
          title="Delete organization?"
          description="This action cannot be undone."
          onConfirm={async () => {
            await deleteOrganization(record.id);
            message.success('Deleted');
            actionRef.current?.reload();
          }}
        >
          <a style={{ color: 'red' }}>Delete</a>
        </Popconfirm>,
      ],
    },
  ];

  return (
    <PageContainer>
      <ProTable
        columns={columns}
        actionRef={actionRef}
        request={async (params, sort, filter) => {
          const data = await listOrganizations({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            search: params.name,
          });
          return {
            data,
            success: true,
            total: data.length, // In a real app, backend should return total
          };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        headerTitle="System Organizations"
        toolBarRender={() => [
          <ModalForm
            key="create"
            title="Create New Organization"
            trigger={
              <Button type="primary">
                <PlusOutlined /> New Organization
              </Button>
            }
            onFinish={async (values: any) => {
              await createOrganization(values);
              message.success('Created successfully');
              actionRef.current?.reload();
              return true;
            }}
          >
            <ProFormText name="name" label="Name" placeholder="Enter organization name" />
            <ProFormSelect
              name="plan_type"
              label="Plan"
              initialValue="free"
              options={[
                { label: 'Free', value: 'free' },
                { label: 'Pro', value: 'pro' },
                { label: 'Enterprise', value: 'enterprise' },
              ]}
            />
          </ModalForm>,
        ]}
      />
    </PageContainer>
  );
};
