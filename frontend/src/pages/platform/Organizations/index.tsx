import { PageContainer, ProTable } from '@ant-design/pro-components';
import { getMyOrganizations } from '@/services/api/admin';
import type { ProColumns } from '@ant-design/pro-components';

const columns: ProColumns[] = [
  { title: 'Name', dataIndex: 'name' },
  { title: 'Plan', dataIndex: 'plan_type', filters: true, valueEnum: {
    free: { text: 'Free', status: 'Default' },
    pro: { text: 'Pro', status: 'Success' },
    enterprise: { text: 'Enterprise', status: 'Processing' },
  }},
  { title: 'Quota Limit', dataIndex: 'quota_tokens_limit' },
  { title: 'Quota Used', dataIndex: 'quota_tokens_used' },
  {
    title: 'Created At',
    dataIndex: 'created_at',
    valueType: 'dateTime',
    sorter: true,
  },
];

export default () => {
  return (
    <PageContainer>
      <ProTable
        columns={columns}
        request={async () => {
          const data = await getMyOrganizations();
          return { data, success: true, total: data.length };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        pagination={{ pageSize: 20 }}
        headerTitle="Organizations"
      />
    </PageContainer>
  );
};
