import { PageContainer, ProTable } from '@ant-design/pro-components';
import { listAuditLogs } from '@/services/api/admin';
import type { ProColumns } from '@ant-design/pro-components';
import { Tag } from 'antd';

const columns: ProColumns[] = [
  {
    title: 'Action',
    dataIndex: 'action',
    render: (text: string) => {
      const color = text.includes('delete') ? 'red' : text.includes('update') ? 'orange' : 'blue';
      return <Tag color={color}>{text.toUpperCase()}</Tag>;
    },
  },
  {
    title: 'Resource',
    dataIndex: 'resource_type',
    render: (text: string, record) => (
      <span>
        {text} <small style={{ color: '#999' }}>#{record.resource_id}</small>
      </span>
    ),
  },
  { title: 'User ID', dataIndex: 'user_id', copyable: true, width: 180 },
  { title: 'IP Address', dataIndex: 'ip_address', width: 120 },
  {
    title: 'Timestamp',
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
          const data = await listAuditLogs({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            action: params.action,
            resource_type: params.resource_type,
          });
          return { data, success: true, total: data.length };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        expandable={{
          expandedRowRender: (record) => (
            <div style={{ padding: '8px 40px' }}>
              <pre style={{ backgroundColor: '#f5f5f5', padding: 12, borderRadius: 4 }}>
                {record.details || 'No additional details'}
              </pre>
            </div>
          ),
        }}
        headerTitle="System Audit Trails"
      />
    </PageContainer>
  );
};
