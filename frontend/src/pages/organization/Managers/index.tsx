import { PageContainer, ProTable } from '@ant-design/pro-components';
import { Tag } from 'antd';
import { listManagers } from '@/services/api/organization';
import type { ProColumns } from '@ant-design/pro-components';

const columns: ProColumns[] = [
  { title: 'Name', dataIndex: 'name' },
  { title: 'Email', dataIndex: 'email', copyable: true },
  { title: 'Title', dataIndex: 'title' },
  {
    title: 'Status',
    dataIndex: 'is_active',
    render: (_, record: any) => (
      <Tag color={record.is_active ? 'green' : 'red'}>
        {record.is_active ? 'Active' : 'Inactive'}
      </Tag>
    ),
  },
  { title: 'Patients Assigned', dataIndex: 'assigned_patient_count' },
];

export default () => {
  return (
    <PageContainer>
      <ProTable
        columns={columns}
        request={async () => {
          const data = await listManagers();
          return { data, success: true, total: data.length };
        }}
        rowKey="id"
        search={false}
        headerTitle="Managers"
      />
    </PageContainer>
  );
};
