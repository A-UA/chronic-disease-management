import { PageContainer } from '@ant-design/pro-components';
import { Card, Tag, List, Spin, Empty } from 'antd';
import { useEffect, useState } from 'react';
import { listRoles } from '@/services/api/organization';

export default () => {
  const [roles, setRoles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listRoles()
      .then(setRoles)
      .catch(() => setRoles([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <PageContainer>
      <Spin spinning={loading}>
        {roles.length === 0 ? (
          <Empty description="No roles found or API not available" />
        ) : (
          <List
            grid={{ gutter: 16, xs: 1, sm: 1, md: 2, lg: 2, xl: 3 }}
            dataSource={roles}
            renderItem={(role: any) => (
              <List.Item>
                <Card title={role.name} extra={role.is_system ? <Tag color="blue">System</Tag> : null}>
                  <p style={{ color: '#666' }}>{role.description}</p>
                  <div>
                    <p style={{ fontWeight: 'bold', marginBottom: 4 }}>Permissions:</p>
                    {(role.permissions || []).map((p: any) => (
                      <Tag key={p.code || p} style={{ marginBottom: 4 }}>
                        {p.name || p}
                      </Tag>
                    ))}
                  </div>
                </Card>
              </List.Item>
            )}
          />
        )}
      </Spin>
    </PageContainer>
  );
};
