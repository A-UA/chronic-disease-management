import React, { useState, useEffect } from 'react';
import { Upload, Button, message, List, Tag, Progress, Space } from 'antd';
import { UploadOutlined, FileTextOutlined, CheckCircleOutlined, SyncOutlined, CloseCircleOutlined } from '@ant-design/icons';
import client from '../../api/client';

interface DocUploadProps {
  kbId: string;
  onSuccess?: () => void;
}

const DocUpload: React.FC<DocUploadProps> = ({ kbId, onSuccess }) => {
  const [uploading, setUploading] = useState(false);
  const [docs, setDocs] = useState<any[]>([]);

  // 轮询检查解析状态
  useEffect(() => {
    const timer = setInterval(async () => {
      const pendingDocs = docs.filter(d => d.status === 'processing');
      if (pendingDocs.length === 0) return;

      for (const doc of pendingDocs) {
        try {
          const response = await client.get(`/documents/${doc.id}`);
          if (response.data.status !== 'processing') {
            setDocs(prev => prev.map(d => d.id === doc.id ? response.data : d));
            if (response.data.status === 'completed') {
              message.success(`文档 ${doc.name} 解析完成`);
              onSuccess?.();
            } else if (response.data.status === 'failed') {
              message.error(`文档 ${doc.name} 解析失败: ${response.data.failed_reason}`);
            }
          }
        } catch (error) {
          console.error('Polling error:', error);
        }
      }
    }, 3000);

    return () => clearInterval(timer);
  }, [docs, onSuccess]);

  const handleUpload = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('kb_id', kbId);

    setUploading(true);
    try {
      // 假设后端接口为 /documents/upload
      const response = await client.post('/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setDocs(prev => [response.data, ...prev]);
      message.info(`文件 ${file.name} 已上传，正在解析中...`);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '上传失败');
    } finally {
      setUploading(false);
    }
    return false; // 阻止 antd 自动上传
  };

  const getStatusTag = (status: string) => {
    switch (status) {
      case 'completed': return <Tag color="success" icon={<CheckCircleOutlined />}>已完成</Tag>;
      case 'processing': return <Tag color="processing" icon={<SyncOutlined spin />}>解析中</Tag>;
      case 'failed': return <Tag color="error" icon={<CloseCircleOutlined />}>失败</Tag>;
      default: return <Tag color="default">{status}</Tag>;
    }
  };

  return (
    <div className="mt-4">
      <Upload beforeUpload={handleUpload} showUploadList={false} disabled={uploading}>
        <Button icon={<UploadOutlined />} loading={uploading} type="primary" ghost>
          选择并上传文档 (PDF/Docx/Txt)
        </Button>
      </Upload>

      <List
        className="mt-4"
        size="small"
        bordered
        header={<div>最近上传列表</div>}
        dataSource={docs}
        renderItem={item => (
          <List.Item>
            <Space className="w-full justify-between">
              <Space>
                <FileTextOutlined />
                <span>{item.name}</span>
              </Space>
              {getStatusTag(item.status)}
            </Space>
          </List.Item>
        )}
      />
    </div>
  );
};

export default DocUpload;
