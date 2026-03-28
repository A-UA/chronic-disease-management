import { PageContainer, ProTable } from '@ant-design/pro-components';
import { listUsers } from '@/services/api/admin';
import type { ProColumns } from '@ant-design/pro-components';

const columns: ProColumns[] = [
  { title: 'Email', dataIndex: 'email', copyable: true },
  { title: 'Name', dataIndex: 'name' },
  { title: 'Organizations', dataIndex: 'org_count', sorter: true },
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
        request={async (params) => {
          const data = await listUsers({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            search: params.keyword,
          });
          return { data, success: true, total: data.length };
        }}
        rowKey="id"
        search={{
          labelWidth: 'auto',
          defaultCollapsed: false,
        }}
        pagination={{ pageSize: 20 }}
        headerTitle="Platform Users"
      />
    </PageContainer>
  );
};
