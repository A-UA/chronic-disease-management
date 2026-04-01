import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { listOrgMembers } from '@/services/api/organization';
import type { ProColumns } from '@ant-design/pro-components';

const columns: ProColumns[] = [
  { title: 'Email', dataIndex: 'email', copyable: true },
  { title: 'Name', dataIndex: 'name' },
  {
    title: 'Type',
    dataIndex: 'user_type',
    render: (_, record: any) => (
      <Tag color={record.user_type === 'staff' ? 'blue' : 'green'}>
        {record.user_type}
      </Tag>
    ),
    filters: [
      { text: 'Staff', value: 'staff' },
      { text: 'Patient', value: 'patient' },
    ],
  },
  {
    title: 'Roles',
    dataIndex: 'roles',
    render: (_, record: any) =>
      (record.roles || []).map((r: string) => <Tag key={r}>{r}</Tag>),
  },
];

export default () => {
  const orgId = localStorage.getItem('currentOrgId') || '';

  return (
    <PageContainer>
      <ProTable
        columns={columns}
        request={async () => {
          if (!orgId) return { data: [], success: true };
          const data = await listOrgMembers(orgId);
          return { data, success: true, total: data.length };
        }}
        rowKey="user_id"
        search={false}
        headerTitle="Organization Members"
      />
    </PageContainer>
  );
};
