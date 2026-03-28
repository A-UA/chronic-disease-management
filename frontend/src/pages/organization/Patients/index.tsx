import { PageContainer, ProTable } from '@ant-design/pro-components';
import { listPatients } from '@/services/api/organization';
import type { ProColumns } from '@ant-design/pro-components';

const columns: ProColumns[] = [
  { title: 'Name', dataIndex: 'real_name' },
  { title: 'Gender', dataIndex: 'gender', filters: [
    { text: 'Male', value: 'male' },
    { text: 'Female', value: 'female' },
  ]},
  { title: 'Birth Date', dataIndex: 'birth_date', valueType: 'date' },
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
          const data = await listPatients({
            skip: ((params.current || 1) - 1) * (params.pageSize || 20),
            limit: params.pageSize || 20,
            search: params.real_name,
          });
          return { data, success: true, total: data.length };
        }}
        rowKey="id"
        search={{ labelWidth: 'auto' }}
        pagination={{ pageSize: 20 }}
        headerTitle="Patients"
      />
    </PageContainer>
  );
};
