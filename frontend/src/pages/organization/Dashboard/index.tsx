import { PageContainer, StatisticCard } from '@ant-design/pro-components';
import { Row, Col, Card, Progress } from 'antd';
import { useEffect, useState } from 'react';
import { listPatients, listKnowledgeBases, listConversations } from '@/services/api/organization';

export default () => {
  const [patientCount, setPatientCount] = useState(0);
  const [kbCount, setKbCount] = useState(0);
  const [convCount, setConvCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      listPatients().then((d) => setPatientCount(d.length)),
      listKnowledgeBases().then((d) => setKbCount(d.length)),
      listConversations({ limit: 1 }).then((d) => setConvCount(d.length)),
    ]).finally(() => setLoading(false));
  }, []);

  return (
    <PageContainer>
      <Row gutter={16}>
        <Col span={8}>
          <StatisticCard
            statistic={{ title: 'Patients', value: patientCount, loading }}
          />
        </Col>
        <Col span={8}>
          <StatisticCard
            statistic={{ title: 'Knowledge Bases', value: kbCount, loading }}
          />
        </Col>
        <Col span={8}>
          <StatisticCard
            statistic={{ title: 'Conversations', value: convCount, loading }}
          />
        </Col>
      </Row>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="Quota Usage" loading={loading}>
            <Progress percent={30} status="active" />
            <p style={{ marginTop: 8, color: '#999' }}>
              300,000 / 1,000,000 tokens used
            </p>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Recent Activity" loading={loading}>
            <p>Organization dashboard ready</p>
          </Card>
        </Col>
      </Row>
    </PageContainer>
  );
};
