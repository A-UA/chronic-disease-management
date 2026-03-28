import {
  PageContainer,
  ProForm,
  ProFormDigit,
  ProFormGroup,
  ProFormSelect,
  ProFormSwitch,
  ProFormText,
} from '@ant-design/pro-components';
import { Card, message, Spin } from 'antd';
import { useEffect, useState } from 'react';
import { getSettings, updateSettings } from '@/services/api/admin';

export default () => {
  const [initialValues, setInitialValues] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSettings()
      .then(setInitialValues)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin size="large" />;

  return (
    <PageContainer>
      <Card title="System Configuration" style={{ maxWidth: 800, margin: '0 auto' }}>
        <ProForm
          initialValues={initialValues}
          onFinish={async (values) => {
            await updateSettings(values);
            message.success('Settings saved successfully');
            return true;
          }}
        >
          <ProFormGroup title="Model & RAG" size={24}>
            <ProFormSelect
              name="llm_default_model"
              label="Default LLM Model"
              width="md"
              options={[
                { label: 'GPT-4o Mini', value: 'gpt-4o-mini' },
                { label: 'GPT-4o', value: 'gpt-4o' },
                { label: 'Claude 3.5 Sonnet', value: 'claude-3-5-sonnet' },
              ]}
            />
            <ProFormDigit
              name="rag_max_chunks"
              label="Max Retrieval Chunks"
              min={1}
              max={20}
              width="xs"
            />
          </ProFormGroup>

          <ProFormGroup title="System Policies" size={24}>
            <ProFormSwitch
              name="system_maintenance_mode"
              label="Maintenance Mode"
              extra="Disable all user access temporarily"
            />
            <ProFormSwitch
              name="allow_new_registrations"
              label="Allow New Registrations"
              extra="Whether to allow users to sign up via public page"
            />
          </ProFormGroup>

          <ProFormGroup title="Resource Quotas" size={24}>
            <ProFormDigit
              name="default_org_token_quota"
              label="Default Org Token Quota"
              width="md"
              addonAfter="Tokens"
            />
          </ProFormGroup>
        </ProForm>
      </Card>
    </PageContainer>
  );
};
