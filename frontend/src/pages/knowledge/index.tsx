import { PageContainer } from '@ant-design/pro-components';
import { Card, Col, Row, Tag, Empty, Spin } from 'antd';
import { useEffect, useState } from 'react';
import { listKnowledgeBases } from '@/services/api/organization';

export default () => {
  const [kbs, setKbs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listKnowledgeBases()
      .then(setKbs)
      .finally(() => setLoading(false));
  }, []);

  return (
    <PageContainer>
      <Spin spinning={loading}>
        {kbs.length === 0 ? (
          <Empty description="No knowledge bases" />
        ) : (
          <Row gutter={[16, 16]}>
            {kbs.map((kb) => (
              <Col key={kb.id} xs={24} sm={12} md={8} lg={6}>
                <Card
                  title={kb.name}
                  extra={<Tag>{kb.document_count} docs</Tag>}
                  hoverable
                >
                  <p>{kb.description || 'No description'}</p>
                  <p style={{ color: '#999', fontSize: 12 }}>
                    Created: {new Date(kb.created_at).toLocaleDateString()}
                  </p>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>
    </PageContainer>
  );
};
