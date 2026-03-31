import { PageContainer, ProTable } from '@ant-design/pro-components';
import { listConversations } from '@/services/api/organization';
import type { ProColumns } from '@ant-design/pro-components';

const columns: ProColumns[] = [
  { title: 'Title', dataIndex: 'title', ellipsis: true },
  { title: 'User ID', dataIndex: 'user_id', copyable: true },
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
          const data = await listConversations({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
          });
          return { data, success: true, total: data.length };
        }}
        rowKey="id"
        search={false}
        pagination={{ pageSize: 20 }}
        headerTitle="Conversations"
      />
    </PageContainer>
  );
};
