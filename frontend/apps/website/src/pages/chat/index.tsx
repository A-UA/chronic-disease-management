import { useState, useEffect, useRef, useCallback } from "react";
import { Card, Input, Button, List, Select, App, Space, Typography, Spin, Tag } from "antd";
import { SendOutlined, RobotOutlined, UserOutlined, PlusOutlined } from "@ant-design/icons";
import { listConversations, getConversation, sendChat, type ChatConversation } from "@/api/chat";
import { listKBs, type KnowledgeBase } from "@/api/knowledge";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function AIChatPage() {
  const [kbList, setKBList] = useState<KnowledgeBase[]>([]);
  const [selectedKB, setSelectedKB] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [currentConvId, setCurrentConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const { message: appMsg } = App.useApp();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 加载知识库
  useEffect(() => {
    void listKBs()
      .then((list) => {
        setKBList(list);
        if (list.length > 0) setSelectedKB(list[0].id);
      })
      .catch(() => void appMsg.error("加载知识库失败"));
  }, []);

  // 加载对话列表
  useEffect(() => {
    void listConversations()
      .then(setConversations)
      .catch(() => {});
  }, []);

  // 自动滚动
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /** 新建对话：清空消息和当前对话 ID，下次发送时由服务端创建 */
  const newConversation = () => {
    setCurrentConvId(null);
    setMessages([]);
  };

  /** 切换到已有对话：加载历史消息 */
  const loadConversation = async (convId: string) => {
    setCurrentConvId(convId);
    setMessages([]);
    try {
      const data = await getConversation(convId);
      setMessages(data.messages.map((m) => ({ role: m.role, content: m.content })));
    } catch {
      void appMsg.error("加载对话消息失败");
    }
  };

  const handleSend = useCallback(async () => {
    if (!input.trim() || !selectedKB || streaming) return;
    const query = input.trim();
    setInput("");

    setMessages((prev) => [...prev, { role: "user", content: query }]);
    setStreaming(true);

    try {
      // conversation_id 为 null 时不传，服务端自动创建新对话
      const response = await sendChat({
        kb_id: selectedKB,
        query,
        ...(currentConvId ? { conversation_id: currentConvId } : {}),
      });

      if (!response.ok || !response.body) {
        void appMsg.error("请求失败");
        setStreaming(false);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantContent = "";
      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // 保留最后一个可能不完整的行
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;

          try {
            const payload = JSON.parse(line.slice(6)) as Record<string, unknown>;

            // meta 事件：从服务端获取 conversation_id
            if ("conversation_id" in payload && typeof payload.conversation_id === "string") {
              setCurrentConvId(payload.conversation_id);
            }

            // chunk 事件：追加流式文本
            if ("text" in payload && typeof payload.text === "string") {
              assistantContent += payload.text;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: assistantContent,
                };
                return updated;
              });
            }

            // done 事件：刷新对话列表
            if ("tokens" in payload) {
              void listConversations()
                .then(setConversations)
                .catch(() => {});
            }
          } catch {
            // 非 JSON data 行，忽略
          }
        }
      }
    } catch {
      void appMsg.error("对话出错");
    } finally {
      setStreaming(false);
    }
  }, [input, selectedKB, currentConvId, streaming]);

  return (
    <div style={{ display: "flex", height: "calc(100vh - 120px)", gap: 16 }}>
      {/* 左侧对话列表 */}
      <Card
        style={{ width: 260, flexShrink: 0, overflow: "auto" }}
        title="对话列表"
        extra={
          <Button type="text" icon={<PlusOutlined />} onClick={newConversation} size="small" />
        }
        styles={{ body: { padding: "8px 0" } }}
      >
        <List
          dataSource={conversations}
          renderItem={(conv) => (
            <List.Item
              key={conv.id}
              onClick={() => void loadConversation(conv.id)}
              style={{
                padding: "8px 16px",
                cursor: "pointer",
                backgroundColor: currentConvId === conv.id ? "#f0f5ff" : "transparent",
              }}
            >
              <Typography.Text ellipsis style={{ maxWidth: 200 }}>
                {conv.title || "新对话"}
              </Typography.Text>
            </List.Item>
          )}
          locale={{ emptyText: "暂无对话" }}
        />
      </Card>

      {/* 右侧聊天区 */}
      <Card
        style={{ flex: 1, display: "flex", flexDirection: "column" }}
        styles={{ body: { flex: 1, display: "flex", flexDirection: "column", padding: 0 } }}
        title={
          <Space>
            <RobotOutlined style={{ color: "#667eea" }} />
            <span>AI 问答</span>
            <Select
              value={selectedKB}
              onChange={setSelectedKB}
              style={{ width: 180 }}
              size="small"
              options={kbList.map((kb) => ({ label: kb.name, value: kb.id }))}
              placeholder="选择知识库"
            />
          </Space>
        }
      >
        {/* 消息列表 */}
        <div style={{ flex: 1, overflow: "auto", padding: "16px 24px" }}>
          {messages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                display: "flex",
                justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                marginBottom: 16,
              }}
            >
              <div
                style={{
                  maxWidth: "70%",
                  padding: "10px 16px",
                  borderRadius: 12,
                  backgroundColor: msg.role === "user" ? "#667eea" : "#f5f5f5",
                  color: msg.role === "user" ? "#fff" : "#333",
                  whiteSpace: "pre-wrap",
                  lineHeight: 1.6,
                }}
              >
                <Space style={{ marginBottom: 4 }}>
                  {msg.role === "user" ? (
                    <Tag color="blue" style={{ margin: 0 }}>
                      <UserOutlined /> 你
                    </Tag>
                  ) : (
                    <Tag color="purple" style={{ margin: 0 }}>
                      <RobotOutlined /> AI
                    </Tag>
                  )}
                </Space>
                <div>
                  {msg.content ||
                    (streaming && idx === messages.length - 1 ? <Spin size="small" /> : "")}
                </div>
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区 */}
        <div style={{ padding: "12px 24px", borderTop: "1px solid #f0f0f0" }}>
          <Space.Compact style={{ width: "100%" }}>
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onPressEnter={() => void handleSend()}
              placeholder="输入你的问题..."
              size="large"
              disabled={streaming || !selectedKB}
            />
            <Button
              type="primary"
              icon={<SendOutlined />}
              size="large"
              onClick={() => void handleSend()}
              loading={streaming}
              disabled={!input.trim() || !selectedKB}
            >
              发送
            </Button>
          </Space.Compact>
        </div>
      </Card>
    </div>
  );
}
