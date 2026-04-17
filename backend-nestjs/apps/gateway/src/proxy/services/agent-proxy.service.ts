import { Injectable } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import FormData from 'form-data';
import { v4 as uuidv4 } from 'uuid';
import { NotFoundException } from '@nestjs/common';
import { Response } from 'express';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
  citations?: any[];
}

export interface ChatConversation {
  id: string;
  kb_id: string;
  title: string | null;
  created_at: string;
  messages: ChatMessage[];
  user_id: string;
}

@Injectable()
export class AgentProxyService {
  private agentUrl = process.env.AGENT_URL || 'http://localhost:8000';
  private conversations = new Map<string, ChatConversation>();

  constructor(private readonly httpService: HttpService) {}

  getConversations(userId: string) {
    return Array.from(this.conversations.values())
      .filter((c) => c.user_id === userId)
      .map((c) => ({
        id: c.id,
        kb_id: c.kb_id,
        title: c.title,
        created_at: c.created_at,
      }))
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }

  getConversation(id: string, userId: string) {
    const conv = this.conversations.get(id);
    if (!conv || conv.user_id !== userId) {
      throw new NotFoundException('Conversation not found');
    }
    return {
      id: conv.id,
      title: conv.title,
      messages: conv.messages,
    };
  }

  deleteConversation(id: string, userId: string) {
    const conv = this.conversations.get(id);
    if (conv && conv.user_id === userId) {
      this.conversations.delete(id);
    }
    return { success: true };
  }

  createConversation(userId: string, kbId: string, title: string | null = null) {
    const conv: ChatConversation = {
      id: uuidv4(),
      kb_id: kbId,
      title: title || '新对话',
      created_at: new Date().toISOString(),
      messages: [],
      user_id: userId,
    };
    this.conversations.set(conv.id, conv);
    return conv;
  }

  async streamChat(
    userId: string,
    query: string,
    kbId: string,
    convId: string | undefined,
    res: Response,
  ) {
    let conv: ChatConversation;
    if (convId) {
      const existing = this.conversations.get(convId);
      if (!existing || existing.user_id !== userId) {
        res.status(404).json({ message: 'Conversation not found' });
        return;
      }
      conv = existing;
    } else {
      conv = this.createConversation(userId, kbId, query.slice(0, 20));
    }

    const payload = {
      query,
      metadata: { kb_id: kbId },
      history: conv.messages.map((m) => ({ role: m.role, content: m.content })),
    };

    conv.messages.push({
      id: uuidv4(),
      role: 'user',
      content: query,
      created_at: new Date().toISOString(),
    });

    try {
      res.setHeader('Content-Type', 'text/event-stream; charset=utf-8');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      res.flushHeaders();

      res.write(`data: ${JSON.stringify({ conversation_id: conv.id })}\n\n`);

      const response = await this.httpService.axiosRef.post(
        `${this.agentUrl}/internal/chat`,
        payload,
        { responseType: 'stream' },
      );

      let assistantContent = '';
      let buffer = '';

      response.data.on('data', (chunk: Buffer) => {
        buffer += chunk.toString();
        let boundary = buffer.indexOf('\n\n');
        
        while (boundary !== -1) {
          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          
          const lines = block.split('\n');
          let currentEvent = 'message';
          let currentData = '';
          
          for (const line of lines) {
            if (line.startsWith('event: ')) {
               currentEvent = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
               currentData += line.slice(6) + '\n';
            }
          }
          if (currentData.endsWith('\n')) {
             currentData = currentData.slice(0, -1);
          }
          
          if (currentEvent === 'message' && currentData) {
             res.write(`data: ${JSON.stringify({ text: currentData })}\n\n`);
             assistantContent += currentData;
          }
          boundary = buffer.indexOf('\n\n');
        }
      });

      response.data.on('end', () => {
        conv.messages.push({
          id: uuidv4(),
          role: 'assistant',
          content: assistantContent,
          created_at: new Date().toISOString(),
        });
        res.write(`data: ${JSON.stringify({ tokens: true })}\n\n`);
        res.end();
      });

      response.data.on('error', (err: any) => {
        console.error('Stream error:', err);
        res.end();
      });
    } catch (e: any) {
      console.error('Chat error:', e.message);
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
        this.httpService.post(`${this.agentUrl}/internal/knowledge/parse`, formData, {
          headers: formData.getHeaders(),
        })
      ) as any;
      if (response.data && response.data.chunk_count !== undefined) {
        return response.data.chunk_count;
      }
    } catch (e: any) {
      console.error('Agent upload failed:', e.message);
    }
    return 0;
  }
}
