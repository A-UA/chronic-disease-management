import { useParams, useNavigate } from "react-router-dom";
import { Card, Descriptions, Button, Spin, Space, Tag } from "antd";
import { ArrowLeftOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { getPatientById } from "@/api/patients";
import HealthTrendChart from "./components/HealthTrendChart";

export default function PatientDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const { data: patient, isLoading } = useQuery({
    queryKey: ["patient", id],
    queryFn: () => getPatientById(id!),
    enabled: !!id,
  });

  if (isLoading || !patient) {
    return <Spin size="large" style={{ display: "block", margin: "100px auto" }} />;
  }

  const genderMap: Record<string, string> = {
    male: "男",
    female: "女",
    other: "其他",
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%", padding: 24 }}>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>
        返回列表
      </Button>

      <Card title="基本信息">
        <Descriptions column={2} bordered>
          <Descriptions.Item label="姓名">{patient.name ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="性别">
            <Tag color={patient.gender === "male" ? "blue" : "pink"}>
              {genderMap[patient.gender ?? ""] ?? "-"}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="出生日期">{patient.birthDate ?? "-"}</Descriptions.Item>
          <Descriptions.Item label="创建时间">{patient.createdAt}</Descriptions.Item>
        </Descriptions>
      </Card>

      <HealthTrendChart patientId={id!} />
    </Space>
  );
}
