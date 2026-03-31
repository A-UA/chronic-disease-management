import { PageContainer, ProTable } from '@ant-design/pro-components';
import { listOrgAuditLogs } from '@/services/api/organization';
import type { ProColumns } from '@ant-design/pro-components';

const columns: ProColumns[] = [
  { title: 'Action', dataIndex: 'action', filters: true },
  { title: 'Resource', dataIndex: 'resource_type', filters: true },
  { title: 'Resource ID', dataIndex: 'resource_id', copyable: true },
  { title: 'Details', dataIndex: 'details', ellipsis: true },
  { title: 'IP Address', dataIndex: 'ip_address' },
  {
    title: 'Time',
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
          const data = await listOrgAuditLogs({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            action: params.action,
            resource_type: params.resource_type,
          });
          return { data, success: true, total: data.length };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        pagination={{ pageSize: 20 }}
        headerTitle="Organization Audit Logs"
      />
    </PageContainer>
  );
};
