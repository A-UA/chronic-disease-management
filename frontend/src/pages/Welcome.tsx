import { PageContainer } from '@ant-design/pro-components';
import { Card, Typography } from 'antd';

export default () => (
  <PageContainer>
    <Card>
      <Typography.Title level={2}>Welcome to Chronic Disease Admin</Typography.Title>
      <Typography.Paragraph>
        Multi-Tenant AI SaaS Management Platform
      </Typography.Paragraph>
      <Typography.Paragraph>
        Use the sidebar to navigate between Platform Admin and Organization management.
      </Typography.Paragraph>
    </Card>
  </PageContainer>
);
