import { Entity, Column, PrimaryColumn, CreateDateColumn } from 'typeorm';

@Entity('chat_messages')
export class ChatMessageEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: string;

  @Column({ name: 'conversation_id', type: 'bigint' })
  conversationId: string;

  @Column({ length: 20 })
  role: 'user' | 'assistant' | 'system';

  @Column({ type: 'text' })
  content: string;

  @Column({ type: 'jsonb', nullable: true })
  citations: Record<string, unknown>[] | null;

  @Column({ type: 'jsonb', nullable: true })
  metadata: Record<string, unknown> | null;

  @Column({ name: 'token_count', type: 'int', default: 0 })
  tokenCount: number;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
