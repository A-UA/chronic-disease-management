import { PageContainer } from '@ant-design/pro-components';
import { Card, Form, Input, Button, message, List, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { getSettings, updateSetting } from '@/services/api/admin';

export default () => {
  const [settings, setSettings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSettings()
      .then(setSettings)
      .finally(() => setLoading(false));
  }, []);

  const handleUpdate = async (key: string, value: string) => {
    try {
      await updateSetting(key, value);
      message.success('Setting updated');
      setSettings((prev) =>
        prev.map((s) => (s.key === key ? { ...s, value } : s)),
      );
    } catch {
      message.error('Failed to update setting');
    }
  };

  return (
    <PageContainer>
      <Card title="System Settings" loading={loading}>
        <List
          dataSource={settings}
          renderItem={(item: any) => (
            <List.Item
              actions={[
                <Button
                  type="link"
                  onClick={() => {
                    const newValue = prompt(`Update ${item.key}:`, item.value);
                    if (newValue !== null) handleUpdate(item.key, newValue);
                  }}
                >
                  Edit
                </Button>,
              ]}
            >
              <List.Item.Meta
                title={<Typography.Text strong>{item.key}</Typography.Text>}
                description={item.description}
              />
              <div>{item.value}</div>
            </List.Item>
          )}
        />
      </Card>
    </PageContainer>
  );
};
