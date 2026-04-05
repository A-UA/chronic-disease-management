import { useState, useEffect, useRef, useCallback, memo } from "react";
import {
  Card,
  Input,
  Button,
  List,
  Select,
  App,
  Space,
  Typography,
  Spin,
  Tag,
  Popover,
} from "antd";
import {
  SendOutlined,
  RobotOutlined,
  UserOutlined,
  PlusOutlined,
  FileTextOutlined,
} from "@ant-design/icons";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { listConversations, getConversation, sendChat, type ChatConversation } from "@/api/chat";
import { listKBs, type KnowledgeBase } from "@/api/knowledge";

/* ================================================================
 *  类型
 * ================================================================ */

interface Citation {
  doc_id: string;
  chunk_id?: string;
  ref: string;
  page?: number;
  snippet: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

/* ================================================================
 *  [Doc n] 引用匹配 — 支持单引用和多引用
 *
 *  匹配模式：
 *    [Doc 1]          → 单个引用
 *    [Doc 1, Doc 3]   → 多个引用
 *    [Doc 1][Doc 3]   → 相邻引用
 * ================================================================ */

// 匹配 [Doc N] 或 [Doc N, Doc M, ...] 两种格式
const DOC_REF_RE = /(\[(?:Doc\s*\d+(?:\s*,\s*Doc\s*\d+)*)\])/gi;
// 从匹配的字符串中提取所有 Doc 编号
const DOC_NUM_RE = /Doc\s*(\d+)/gi;

function extractDocNums(matched: string): number[] {
  const nums: number[] = [];
  let m: RegExpExecArray | null;
  DOC_NUM_RE.lastIndex = 0;
  while ((m = DOC_NUM_RE.exec(matched)) !== null) {
    nums.push(parseInt(m[1], 10));
  }
  return nums;
}

/* ================================================================
 *  引用 Popover 组件
 * ================================================================ */

function DocRefTag({ text, citations }: { text: string; citations: Citation[] }) {
  const nums = extractDocNums(text);
  const matched = nums
    .map((n) => citations.find((c) => c.ref === `Doc ${n}`))
    .filter(Boolean) as Citation[];

  if (matched.length === 0) {
    return (
      <Tag color="geekblue" className="mx-0.5 text-xs cursor-default">
        {text}
      </Tag>
    );
  }

  const popoverContent = (
    <div className="max-w-sm space-y-2">
      {matched.map((c, i) => (
        <div key={i} className="text-xs">
          <div className="font-semibold text-blue-600 mb-0.5 flex items-center gap-1">
            <FileTextOutlined />
            {c.ref}
            {c.page != null && (
              <span className="text-gray-400 font-normal ml-1">第 {c.page} 页</span>
            )}
          </div>
          <div className="text-gray-600 leading-relaxed bg-gray-50 rounded p-2 border border-gray-100">
            {c.snippet || "（无摘要）"}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <Popover
      content={popoverContent}
      title={<span className="text-sm font-semibold">📄 参考来源</span>}
      trigger="click"
      placement="top"
    >
      <Tag
        color="geekblue"
        className="mx-0.5 text-xs cursor-pointer hover:shadow-md transition-shadow"
      >
        {text}
      </Tag>
    </Popover>
  );
}

/* ================================================================
 *  文本中 [Doc n] 替换渲染
 * ================================================================ */

function renderWithDocRefs(text: string, citations: Citation[]) {
  const parts = text.split(DOC_REF_RE);
  return parts.map((part, i) =>
    DOC_REF_RE.test(part) ? (
      <DocRefTag key={i} text={part} citations={citations} />
    ) : (
      <span key={i}>{part}</span>
    ),
  );
}

/* ================================================================
 *  构建 react-markdown 组件（闭包注入 citations）
 * ================================================================ */

function buildMarkdownComponents(citations: Citation[]): Components {
  return {
    p({ children }) {
      if (typeof children === "string") {
        return <p className="mb-2 leading-relaxed">{renderWithDocRefs(children, citations)}</p>;
      }
      const processed = Array.isArray(children)
        ? children.map((child, i) =>
            typeof child === "string" ? (
              <span key={i}>{renderWithDocRefs(child, citations)}</span>
            ) : (
              child
            ),
          )
        : children;
      return <p className="mb-2 leading-relaxed">{processed}</p>;
    },
    li({ children }) {
      if (typeof children === "string") {
        return <li className="mb-1">{renderWithDocRefs(children, citations)}</li>;
      }
      return <li className="mb-1">{children}</li>;
    },
    h1({ children }) {
      return <h1 className="text-lg font-bold mt-4 mb-2 text-gray-800">{children}</h1>;
    },
    h2({ children }) {
      return <h2 className="text-base font-bold mt-3 mb-2 text-gray-800">{children}</h2>;
    },
    h3({ children }) {
      return <h3 className="text-sm font-bold mt-2 mb-1 text-gray-700">{children}</h3>;
    },
    ul({ children }) {
      return <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>;
    },
    ol({ children }) {
      return <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>;
    },
    strong({ children }) {
      return <strong className="font-semibold text-gray-900">{children}</strong>;
    },
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
    blockquote({ children }) {
      return (
        <blockquote className="border-l-4 border-blue-300 pl-4 my-2 text-gray-600 italic">
          {children}
        </blockquote>
      );
    },
  };
}

/* ================================================================
 *  Markdown 消息组件
 * ================================================================ */

const MarkdownMessage = memo(function MarkdownMessage({
  content,
  citations,
  isStreaming,
}: {
  content: string;
  citations: Citation[];
  isStreaming: boolean;
}) {
  const components = buildMarkdownComponents(citations);
  return (
    <div className="text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
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
      let currentCitations: Citation[] = [];
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

            // meta 事件：获取 conversation_id 和 citations
            if ("conversation_id" in payload && typeof payload.conversation_id === "string") {
              setCurrentConvId(payload.conversation_id);
            }
            if ("citations" in payload && Array.isArray(payload.citations)) {
              currentCitations = payload.citations as Citation[];
            }

            // chunk 事件
            if ("text" in payload && typeof payload.text === "string") {
              assistantContent += payload.text;
              setMessages((prev) => {
                const updated = [...prev];
                updated[updated.length - 1] = {
                  role: "assistant",
                  content: assistantContent,
                  citations: currentCitations,
                };
                return updated;
              });
            }

            // done 事件
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
              options={kbList.map((kb) => ({
                label: kb.name,
                value: kb.id,
              }))}
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
                    citations={msg.citations ?? []}
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
