import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, DataSource } from 'typeorm';
import { ConversationEntity } from './entities/conversation.entity.js';
import { ChatMessageEntity } from './entities/chat-message.entity.js';
import { nextId } from '@cdm/shared';
import type {
  ConversationVO,
  ConversationDetailVO,
  ChatMessageVO,
  CitationVO,
} from '@cdm/shared';
import type { CitationData } from '@cdm/shared';

@Injectable()
export class ConversationService {
  constructor(
    @InjectRepository(ConversationEntity) private convRepo: Repository<ConversationEntity>,
    @InjectRepository(ChatMessageEntity) private msgRepo: Repository<ChatMessageEntity>,
    private dataSource: DataSource,
  ) {}

  async findAll(tenantId: string, userId: string): Promise<ConversationVO[]> {
    const entities = await this.convRepo.find({
      where: { tenantId, userId },
      order: { lastMessageAt: 'DESC' },
    });
    return entities.map(ConversationService.toConvVO);
  }

  async findOne(id: string, tenantId: string, userId: string): Promise<ConversationDetailVO | null> {
    const conv = await this.convRepo.findOne({ where: { id, tenantId, userId } });
    if (!conv) return null;

    const messages = await this.msgRepo.find({
      where: { conversationId: id },
      order: { createdAt: 'ASC' },
    });

    return {
      ...ConversationService.toConvVO(conv),
      messages: messages.map(ConversationService.toMsgVO),
    };
  }

  async create(tenantId: string, orgId: string, userId: string, kbId?: string, title?: string): Promise<ConversationVO> {
    const conv = this.convRepo.create({
      id: nextId(),
      tenantId,
      orgId,
      userId,
      kbId: kbId ?? null,
      title: title ?? '新对话',
    });
    const saved = await this.convRepo.save(conv);
    return ConversationService.toConvVO(saved);
  }

  async delete(id: string, tenantId: string, userId: string): Promise<{ affected: number }> {
    const result = await this.convRepo.delete({ id, tenantId, userId });
    return { affected: result.affected ?? 0 };
  }

  async createMessage(
    conversationId: string,
    role: 'user' | 'assistant' | 'system',
    content: string,
    citations?: CitationData[],
    metadata?: Record<string, unknown>,
    tokenCount?: number,
  ): Promise<ChatMessageVO> {
    const tc = tokenCount ?? 0;

    return this.dataSource.transaction(async (manager) => {
      const msg = manager.create(ChatMessageEntity, {
        id: nextId(),
        conversationId,
        role,
        content,
        citations: (citations ?? null) as unknown as Record<string, unknown>[] | null,
        metadata: metadata ?? null,
        tokenCount: tc,
      });
      const saved = await manager.save(msg);

      // 更新会话统计
      await manager.increment(ConversationEntity, { id: conversationId }, 'messageCount', 1);
      await manager.increment(ConversationEntity, { id: conversationId }, 'totalTokens', tc);
      await manager.update(ConversationEntity, { id: conversationId }, { lastMessageAt: new Date() });

      return ConversationService.toMsgVO(saved);
    });
  }

  static toConvVO(entity: ConversationEntity): ConversationVO {
    return {
      id: entity.id,
      tenantId: entity.tenantId,
      orgId: entity.orgId,
      userId: entity.userId,
      kbId: entity.kbId,
      title: entity.title,
      messageCount: entity.messageCount,
      totalTokens: entity.totalTokens,
      lastMessageAt: entity.lastMessageAt,
      createdAt: entity.createdAt,
    };
  }

  static toMsgVO(entity: ChatMessageEntity): ChatMessageVO {
    return {
      id: entity.id,
      conversationId: entity.conversationId,
      role: entity.role,
      content: entity.content,
      citations: (entity.citations ?? null) as unknown as CitationVO[] | null,
      metadata: entity.metadata,
      tokenCount: entity.tokenCount,
      createdAt: entity.createdAt,
    };
  }
}
