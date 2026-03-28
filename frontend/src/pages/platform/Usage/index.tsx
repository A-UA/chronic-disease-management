import { PageContainer, ProTable } from '@ant-design/pro-components';
import { getUsageSummary } from '@/services/api/admin';
import type { ProColumns } from '@ant-design/pro-components';

const columns: ProColumns[] = [
  { title: 'Organization', dataIndex: 'org_name' },
  { title: 'Total Tokens', dataIndex: 'total_tokens', sorter: true },
  {
    title: 'Total Cost',
    dataIndex: 'total_cost',
    render: (_, record) => `$${(record.total_cost || 0).toFixed(4)}`,
  },
];

export default () => {
  return (
    <PageContainer>
      <ProTable
        columns={columns}
        request={async () => {
          const data = await getUsageSummary();
          return { data, success: true, total: data.length };
        }}
        rowKey="org_id"
        search={false}
        pagination={{ pageSize: 20 }}
        headerTitle="Token Usage by Organization"
      />
    </PageContainer>
  );
};
