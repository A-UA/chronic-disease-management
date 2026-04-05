import { useState, useEffect, useRef, useCallback, memo } from "react";
import { Card, Input, Button, List, Select, App, Space, Typography, Spin, Tag } from "antd";
import { SendOutlined, RobotOutlined, UserOutlined, PlusOutlined } from "@ant-design/icons";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { listConversations, getConversation, sendChat, type ChatConversation } from "@/api/chat";
import { listKBs, type KnowledgeBase } from "@/api/knowledge";

/* ================================================================
 *  类型
 * ================================================================ */

interface Message {
  role: "user" | "assistant";
  content: string;
}

/* ================================================================
 *  Markdown 自定义组件：[Doc n] 引用高亮
 * ================================================================ */

/**
 * 将文本中的 [Doc n] 替换为蓝色 Tag。
 * 作为 react-markdown 的自定义 text/paragraph 渲染器使用。
 */
function renderWithDocRefs(text: string) {
  const parts = text.split(/(\[Doc\s*\d+\])/gi);
  return parts.map((part, i) =>
    /^\[Doc\s*\d+\]$/i.test(part) ? (
      <Tag key={i} color="geekblue" className="mx-0.5 text-xs cursor-default">
        {part}
      </Tag>
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

/** react-markdown 自定义组件映射 */
const markdownComponents: Components = {
  // 段落：嵌入 [Doc n] 引用标签
  p({ children }) {
    if (typeof children === "string") {
      return <p className="mb-2 leading-relaxed">{renderWithDocRefs(children)}</p>;
    }
    // children 可能是混合节点（包含 strong/em 等）
    const processed = Array.isArray(children)
      ? children.map((child, i) =>
          typeof child === "string" ? <span key={i}>{renderWithDocRefs(child)}</span> : child,
        )
      : children;
    return <p className="mb-2 leading-relaxed">{processed}</p>;
  },
  // 列表项：也处理 [Doc n]
  li({ children }) {
    if (typeof children === "string") {
      return <li className="mb-1">{renderWithDocRefs(children)}</li>;
    }
    return <li className="mb-1">{children}</li>;
  },
  // 标题样式
  h1({ children }) {
    return <h1 className="text-lg font-bold mt-4 mb-2 text-gray-800">{children}</h1>;
  },
  h2({ children }) {
    return <h2 className="text-base font-bold mt-3 mb-2 text-gray-800">{children}</h2>;
  },
  h3({ children }) {
    return <h3 className="text-sm font-bold mt-2 mb-1 text-gray-700">{children}</h3>;
  },
  // 列表容器
  ul({ children }) {
    return <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>;
  },
  ol({ children }) {
    return <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>;
  },
  // 粗体
  strong({ children }) {
    return <strong className="font-semibold text-gray-900">{children}</strong>;
  },
  // 代码块
  code({ className, children }) {
    const isInline = !className;
    if (isInline) {
      return (
        <code className="bg-gray-100 text-red-600 rounded px-1 py-0.5 text-xs font-mono">
          {children}
        </code>
      );
    }
    return (
      <pre className="bg-gray-900 text-gray-100 rounded-lg p-4 overflow-x-auto text-sm my-2">
        <code className="font-mono">{children}</code>
      </pre>
    );
  },
  // 表格
  table({ children }) {
    return (
      <div className="overflow-x-auto my-2">
        <table className="min-w-full border border-gray-200 text-sm">{children}</table>
      </div>
    );
  },
  th({ children }) {
    return (
      <th className="bg-gray-50 border border-gray-200 px-3 py-2 text-left font-semibold">
        {children}
      </th>
    );
  },
  td({ children }) {
    return <td className="border border-gray-200 px-3 py-2">{children}</td>;
  },
  // 引用块
  blockquote({ children }) {
    return (
      <blockquote className="border-l-4 border-blue-300 pl-4 my-2 text-gray-600 italic">
        {children}
      </blockquote>
    );
  },
};

/* ================================================================
 *  Markdown 消息组件（带 memo 优化）
 * ================================================================ */

const MarkdownMessage = memo(function MarkdownMessage({
  content,
  isStreaming,
}: {
  content: string;
  isStreaming: boolean;
}) {
  return (
    <div className="text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
      {isStreaming && !content && <Spin size="small" />}
    </div>
  );
});

/* ================================================================
 *  主页面
 * ================================================================ */

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

  useEffect(() => {
    void listKBs()
      .then((list) => {
        setKBList(list);
        if (list.length > 0) setSelectedKB(list[0].id);
      })
      .catch(() => void appMsg.error("加载知识库失败"));
  }, []);

  useEffect(() => {
    void listConversations()
      .then(setConversations)
      .catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const newConversation = () => {
    setCurrentConvId(null);
    setMessages([]);
  };

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
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;

          try {
            const payload = JSON.parse(line.slice(6)) as Record<string, unknown>;

            if ("conversation_id" in payload && typeof payload.conversation_id === "string") {
              setCurrentConvId(payload.conversation_id);
            }

            if ("text" in payload && typeof payload.text === "string") {
              assistantContent += payload.text;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = { role: "assistant", content: assistantContent };
                return updated;
              });
            }

            if ("tokens" in payload) {
              void listConversations()
                .then(setConversations)
                .catch(() => {});
            }
          } catch {
            // 忽略非 JSON 行
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
    <div className="flex gap-4" style={{ height: "calc(100vh - 120px)" }}>
      {/* 左侧对话列表 */}
      <Card
        className="w-[260px] shrink-0 overflow-auto"
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
              className="cursor-pointer transition-colors hover:bg-blue-50"
              style={{
                padding: "8px 16px",
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
        className="flex-1 flex flex-col min-w-0 overflow-hidden"
        styles={{
          body: {
            flex: 1,
            display: "flex",
            flexDirection: "column",
            padding: 0,
            overflow: "hidden",
          },
        }}
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
        <div className="flex-1 overflow-auto px-6 py-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex mb-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className="min-w-0 rounded-xl"
                style={{
                  maxWidth: msg.role === "user" ? "70%" : "85%",
                  padding: msg.role === "user" ? "10px 16px" : "16px 20px",
                  backgroundColor: msg.role === "user" ? "#667eea" : "#f8f9fa",
                  color: msg.role === "user" ? "#fff" : "#333",
                }}
              >
                <Space className="mb-1">
                  {msg.role === "user" ? (
                    <Tag color="blue" className="!m-0">
                      <UserOutlined /> 你
                    </Tag>
                  ) : (
                    <Tag color="purple" className="!m-0">
                      <RobotOutlined /> AI
                    </Tag>
                  )}
                </Space>

                {msg.role === "assistant" ? (
                  <MarkdownMessage
                    content={msg.content}
                    isStreaming={streaming && idx === messages.length - 1}
                  />
                ) : (
                  <div className="whitespace-pre-wrap break-words leading-relaxed">
                    {msg.content}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* 输入区 */}
        <div className="px-6 py-3 border-t border-gray-100">
          <Space.Compact className="w-full">
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
