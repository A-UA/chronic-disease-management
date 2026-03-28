import { PageContainer, StatisticCard } from '@ant-design/pro-components';
import { Row, Col, Badge, Alert } from 'antd';
import { useEffect, useState } from 'react';
import { getDashboardStats } from '@/services/api/admin';
import { Line } from '@ant-design/charts';

const { Divider } = StatisticCard;

export default () => {
  const [stats, setStats] = useState<any>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardStats()
      .then(setStats)
      .finally(() => setLoading(false));
  }, []);

  const config = {
    data: stats.token_usage_trend || [],
    padding: 'auto' as any,
    xField: 'date',
    yField: 'tokens',
    xAxis: {
      tickCount: 7,
    },
    smooth: true,
  };

  return (
    <PageContainer>
      {stats.recent_failed_docs > 0 && (
        <Alert
          message={`Attention: ${stats.recent_failed_docs} document(s) failed to process in the last batch.`}
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      <StatisticCard.Group direction="row">
        <StatisticCard
          statistic={{
            title: 'Total Organizations',
            value: stats.total_organizations,
            status: 'processing',
          }}
        />
        <Divider type="vertical" />
        <StatisticCard
          statistic={{
            title: 'Active Users (24h)',
            value: stats.active_users_24h,
            status: 'success',
          }}
        />
        <Divider type="vertical" />
        <StatisticCard
          statistic={{
            title: 'Total Conversations',
            value: stats.total_conversations,
          }}
        />
        <Divider type="vertical" />
        <StatisticCard
          statistic={{
            title: 'Total Tokens',
            value: stats.total_tokens_used,
            precision: 0,
            suffix: 'T',
          }}
        />
      </StatisticCard.Group>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={16}>
          <StatisticCard
            title="Token Usage Trend (Last 7 Days)"
            chart={
              <div style={{ height: 300, marginTop: 20 }}>
                {stats.token_usage_trend ? <Line {...config} /> : null}
              </div>
            }
          />
        </Col>
        <Col span={8}>
          <StatisticCard
            title="System Pulse"
            style={{ height: '100%' }}
            footer={
              <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 16 }}>
                <Badge status="processing" text="LLM Service: Healthy" />
                <br />
                <Badge status="processing" text="Vector DB: Connected" />
                <br />
                <Badge status="processing" text="Storage: 14% Used" />
              </div>
            }
          >
            <StatisticCard
              statistic={{
                title: 'Total Patients Managed',
                value: stats.total_patients,
                description: <Badge status="default" text="Across all tenants" />,
              }}
              chartPlacement="left"
            />
          </StatisticCard>
        </Col>
      </Row>
    </PageContainer>
  );
};
