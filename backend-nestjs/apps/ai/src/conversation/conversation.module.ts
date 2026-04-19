import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ConversationEntity } from './entities/conversation.entity.js';
import { ChatMessageEntity } from './entities/chat-message.entity.js';
import { ConversationController } from './conversation.controller.js';
import { ConversationService } from './conversation.service.js';

@Module({
  imports: [TypeOrmModule.forFeature([ConversationEntity, ChatMessageEntity])],
  controllers: [ConversationController],
  providers: [ConversationService],
})
export class ConversationModule {}
