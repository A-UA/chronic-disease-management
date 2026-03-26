import React, { useState, useRef, useEffect } from 'react';
import { Input, Button, List, Card, Space, Typography, Tag, Divider, Spin } from 'antd';
import { SendOutlined, RobotOutlined, UserOutlined, FileSearchOutlined } from '@ant-design/icons';
import { useAuthStore } from '../../stores/auth';

const { Text } = Typography;

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: any[];
  observability?: any;
}

interface ChatPaneProps {
  patientId: string;
  kbId: string;
}

const ChatPane: React.FC<ChatPaneProps> = ({ patientId, kbId }) => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const token = useAuthStore(state => state.token);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    let assistantContent = '';
    const assistantMsg: Message = { role: 'assistant', content: '' };
    setMessages(prev => [...prev, assistantMsg]);

    try {
      // 这里的逻辑对应后端的流式输出。由于使用 Axios 处理流较复杂，这里使用原生 fetch 配合 SSE。
      const response = await fetch(`/api/v1/biz/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: input,
          patient_id: patientId,
          kb_id: kbId,
          stream: true
        })
      });

      if (!response.body) throw new Error('No body');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        // 后端可能按 SSE 格式发送 data: {...}
        const lines = chunk.split('\n');
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6));
            if (data.type === 'content') {
              assistantContent += data.delta;
              setMessages(prev => {
                const last = prev[prev.length - 1];
                return [...prev.slice(0, -1), { ...last, content: assistantContent }];
              });
            } else if (data.type === 'metadata') {
              setMessages(prev => {
                const last = prev[prev.length - 1];
                return [...prev.slice(0, -1), { ...last, citations: data.citations, observability: data.observability }];
              });
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => {
        const last = prev[prev.length - 1];
        return [...prev.slice(0, -1), { ...last, content: last.content + '\n[对话发生错误]' }];
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="h-[600px] flex flex-col p-0 overflow-hidden" bodyStyle={{ padding: 0, height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
        {messages.map((msg, idx) => (
          <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] p-3 rounded-lg shadow-sm ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-white'}`}>
              <Space direction="vertical" size="small" className="w-full">
                <Space>
                  {msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                  <Text strong={msg.role === 'assistant'} style={{ color: msg.role === 'user' ? 'white' : 'inherit' }}>
                    {msg.role === 'user' ? '你' : 'AI 助手'}
                  </Text>
                </Space>
                <div className="whitespace-pre-wrap">{msg.content}</div>
                
                {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-100">
                    <Text type="secondary" size="small">引用来源：</Text>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {msg.citations.map((c, i) => (
                        <Tag key={i} color="blue" className="cursor-pointer">[{c.index || i + 1}] {c.doc_name || '文档'}</Tag>
                      ))}
                    </div>
                  </div>
                )}
              </Space>
            </div>
          </div>
        ))}
        {loading && <div className="text-center"><Spin size="small" /></div>}
      </div>

      <div className="p-4 border-t border-gray-200 bg-white">
        <Space.Compact className="w-full">
          <Input 
            placeholder="输入健康咨询问题..." 
            value={input} 
            onChange={e => setInput(e.target.value)}
            onPressEnter={handleSend}
            disabled={loading}
          />
          <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={loading}>发送</Button>
        </Space.Compact>
      </div>
    </Card>
  );
};

export default ChatPane;
