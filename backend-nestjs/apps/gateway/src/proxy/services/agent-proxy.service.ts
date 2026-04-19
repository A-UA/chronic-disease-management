import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ClientProxy } from '@nestjs/microservices';
import { firstValueFrom, lastValueFrom } from 'rxjs';
import FormData from 'form-data';
import { Response } from 'express';
import { MESSAGE_CREATE, CONVERSATION_FIND_ONE } from '@cdm/shared';
import type { IdentityPayload, ParseDocumentResponse, CitationData, ConversationDetailVO } from '@cdm/shared';

@Injectable()
export class AgentProxyService {
  private agentUrl = process.env.AGENT_URL || 'http://localhost:8000';

  constructor(private readonly httpService: HttpService) {}

  /**
   * 流式聊天 — 消息持久化通过 aiClient TCP 写入 ai-service
   */
  async streamChat(
    identity: IdentityPayload,
    query: string,
    kbId: string,
    conversationId: string,
    aiClient: ClientProxy,
    res: Response,
  ) {
    // 1. 从 ai-service 拉取历史消息
    const convDetail = await lastValueFrom(
      aiClient.send<ConversationDetailVO | null>({ cmd: CONVERSATION_FIND_ONE }, {
        identity,
        id: conversationId,
      }),
    );
    const history = (convDetail?.messages ?? []).map((m) => ({
      role: m.role,
      content: m.content,
    }));

    const payload = {
      query,
      metadata: { kb_id: kbId },
      history,
    };

    // 2. 持久化用户消息
    await lastValueFrom(
      aiClient.send({ cmd: MESSAGE_CREATE }, {
        conversationId,
        role: 'user',
        content: query,
      }),
    );

    try {
      res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      res.flushHeaders();

      // 第一个事件：发送 conversation_id
      res.write(`data: ${JSON.stringify({ conversation_id: conversationId })}\n\n`);

      const response = await this.httpService.axiosRef.post(
        `${this.agentUrl}/internal/chat`,
        payload,
        { responseType: 'stream' },
      );

      let assistantContent = '';
      let citations: CitationData[] = [];
      let buffer = '';

      response.data.on('data', (chunk: Buffer) => {
        buffer += chunk.toString();

        while (true) {
          const idx1 = buffer.indexOf('\n\n');
          const idx2 = buffer.indexOf('\r\n\r\n');

          let boundary = -1;
          let shift = 0;

          if (idx1 !== -1 && idx2 !== -1) {
            if (idx1 < idx2) { boundary = idx1; shift = 2; }
            else { boundary = idx2; shift = 4; }
          } else if (idx1 !== -1) {
            boundary = idx1; shift = 2;
          } else if (idx2 !== -1) {
            boundary = idx2; shift = 4;
          } else {
            break;
          }

          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + shift);

          const lines = block.split('\n');
          let currentEvent = 'message';
          let currentData = '';

          for (const line of lines) {
            const cleanLine = line.replace(/\r$/, '');
            if (cleanLine.startsWith('event: ')) {
              currentEvent = cleanLine.slice(7).trim();
            } else if (cleanLine.startsWith('data: ')) {
              currentData += cleanLine.slice(6) + '\n';
            }
          }
          if (currentData.endsWith('\n')) {
            currentData = currentData.slice(0, -1);
          }

          if (currentEvent === 'message' && currentData) {
            res.write(`data: ${JSON.stringify({ text: currentData })}\n\n`);
            assistantContent += currentData;
          } else if (currentEvent === 'tool_end' && currentData) {
            // 提取 artifact（引用数据）
            try {
              const parsed = JSON.parse(currentData) as { artifact?: CitationData[] };
              if (parsed.artifact) {
                citations = parsed.artifact;
              }
            } catch { /* 忽略非 JSON 的 tool_end */ }
          }
        }
      });

      response.data.on('end', () => {
        // 持久化助手消息
        lastValueFrom(
          aiClient.send({ cmd: MESSAGE_CREATE }, {
            conversationId,
            role: 'assistant',
            content: assistantContent,
            citations: citations.length > 0 ? citations : undefined,
          }),
        ).catch((err: Error) => console.error('Failed to persist assistant message:', err.message));

        // 发送带引用的结束事件
        const donePayload: Record<string, unknown> = { done: true };
        if (citations.length > 0) {
          donePayload.citations = citations;
        }
        res.write(`data: ${JSON.stringify(donePayload)}\n\n`);
        res.end();
      });

      response.data.on('error', (err: Error) => {
        console.error('Stream error:', err);
        res.end();
      });
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      console.error('Chat error:', message);
      if (!res.headersSent) {
        res.status(500).json({ message: 'Chat failed' });
      } else {
        res.end();
      }
    }
  }

  async parseDocument(file: Express.Multer.File, kbId: string): Promise<number> {
    const formData = new FormData();
    formData.append('kb_id', kbId);
    formData.append('file', file.buffer, {
      filename: file.originalname,
      contentType: file.mimetype,
    });

    try {
      const response = await firstValueFrom(
        this.httpService.post<ParseDocumentResponse>(`${this.agentUrl}/internal/knowledge/parse`, formData, {
          headers: formData.getHeaders(),
        }),
      );
      if (response.data?.chunk_count !== undefined) {
        return response.data.chunk_count;
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      console.error('Agent upload failed:', message);
    }
    return 0;
  }
}

