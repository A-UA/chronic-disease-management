import { useState } from "react";
import { Card, Select, Space } from "antd";
import { useQuery } from "@tanstack/react-query";
import { Line } from "@ant-design/charts";
import { getPatientTrend } from "@/api/health-metrics";

const METRIC_OPTIONS = [
  { label: "血压", value: "blood_pressure" },
  { label: "血糖", value: "bloodSugar" },
  { label: "体重", value: "weight" },
  { label: "心率", value: "heartRate" },
  { label: "BMI", value: "bmi" },
  { label: "血氧", value: "spo2" },
];

const DAY_OPTIONS = [
  { label: "近7天", value: 7 },
  { label: "近30天", value: 30 },
  { label: "近90天", value: 90 },
];

export default function HealthTrendChart({ patientId }: { patientId: string }) {
  const [metricType, setMetricType] = useState("blood_pressure");
  const [days, setDays] = useState(30);

  const { data = [], isLoading } = useQuery({
    queryKey: ["patient-trend", patientId, metricType, days],
    queryFn: () => getPatientTrend(patientId, metricType, days),
  });

  const isBloodPressure = metricType === "blood_pressure";
  const chartData = isBloodPressure
    ? data.flatMap((d) => [
        { date: d.measuredAt, value: d.value, type: "收缩压" },
        { date: d.measuredAt, value: d.value_secondary ?? 0, type: "舒张压" },
      ])
    : data.map((d) => ({ date: d.measuredAt, value: d.value, type: metricType }));

  return (
    <Card
      title="健康指标趋势"
      extra={
        <Space>
          <Select
            value={metricType}
            onChange={setMetricType}
            options={METRIC_OPTIONS}
            style={{ width: 100 }}
          />
          <Select value={days} onChange={setDays} options={DAY_OPTIONS} style={{ width: 100 }} />
        </Space>
      }
    >
      <Line
        data={chartData}
        loading={isLoading}
        xField="date"
        yField="value"
        seriesField={isBloodPressure ? "type" : undefined}
        smooth
        point={{ size: 3 }}
        height={300}
      />
    </Card>
  );
}
