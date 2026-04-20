import { useNavigate } from "react-router-dom";
import { ProTable, type ProColumns } from "@ant-design/pro-components";
import { Button, Popconfirm, message } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { getPatients, deletePatient } from "@/api/patients";
import { usePermission } from "@/hooks/usePermission";
import type { PatientProfile } from "@/types/patient";

export default function PatientListPage() {
  const navigate = useNavigate();
  const { hasPermission } = usePermission();

  const handleDelete = async (id: string) => {
    await deletePatient(id);
    message.success("删除成功");
  };

  const columns: ProColumns<PatientProfile>[] = [
    { title: "姓名", dataIndex: "real_name", ellipsis: true },
    {
      title: "性别",
      dataIndex: "gender",
      width: 80,
      valueEnum: { male: { text: "男" }, female: { text: "女" }, other: { text: "其他" } },
    },
    { title: "出生日期", dataIndex: "birth_date", valueType: "date", width: 120 },
    {
      title: "创建时间",
      dataIndex: "createdAt",
      valueType: "dateTime",
      width: 180,
      sorter: true,
      hideInSearch: true,
    },
    {
      title: "操作",
      width: 150,
      valueType: "option",
      render: (_, record) => [
        <a key="view" onClick={() => navigate(`/patients/${record.id}`)}>
          详情
        </a>,
        hasPermission("patient:delete") && (
          <Popconfirm key="del" title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <a style={{ color: "#f5222d" }}>删除</a>
          </Popconfirm>
        ),
      ],
    },
  ];

  return (
    <ProTable<PatientProfile>
      headerTitle="患者列表"
      rowKey="id"
      columns={columns}
      request={async (params) => {
        const data = await getPatients({
          skip: ((params.current ?? 1) - 1) * (params.pageSize ?? 20),
          limit: params.pageSize ?? 20,
          search: params.real_name as string | undefined,
        });
        return { data, success: true };
      }}
      toolBarRender={() => [
        hasPermission("patient:create") ? (
          <Button key="add" type="primary" icon={<PlusOutlined />}>
            新建患者
          </Button>
        ) : null,
      ]}
      pagination={{ defaultPageSize: 20 }}
      search={{ labelWidth: "auto" }}
    />
  );
}
