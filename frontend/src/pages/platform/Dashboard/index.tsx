import { PageContainer, StatisticCard } from '@ant-design/pro-components';
import { Row, Col, Card } from 'antd';
import { useEffect, useState } from 'react';
import { getDashboardStats } from '@/services/api/admin';

export default () => {
  const [stats, setStats] = useState<any>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .finally(() => setLoading(false));
  }, []);

  return (
    <PageContainer>
      <Row gutter={16}>
        <Col span={6}>
          <StatisticCard
            statistic={{
              title: 'Total Organizations',
              value: stats.total_organizations,
              loading,
            }}
          />
        </Col>
        <Col span={6}>
          <StatisticCard
            statistic={{
              title: 'Total Users',
              value: stats.total_users,
              loading,
            }}
          />
        </Col>
        <Col span={6}>
          <StatisticCard
            statistic={{
              title: 'Total Patients',
              value: stats.total_patients,
              loading,
            }}
          />
        </Col>
        <Col span={6}>
          <StatisticCard
            statistic={{
              title: 'Total Tokens Used',
              value: stats.total_tokens_used,
              loading,
            }}
          />
        </Col>
      </Row>
      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={12}>
          <Card title="Total Conversations" loading={loading}>
            <p style={{ fontSize: 32, fontWeight: 'bold', textAlign: 'center' }}>
              {stats.total_conversations || 0}
            </p>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="System Status" loading={loading}>
            <p style={{ fontSize: 16, textAlign: 'center', color: 'green' }}>
              All services operational
            </p>
          </Card>
        </Col>
      </Row>
    </PageContainer>
  );
};
