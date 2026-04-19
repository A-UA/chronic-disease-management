import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { ConversationService } from './conversation.service.js';
import {
  CONVERSATION_FIND_ALL, CONVERSATION_FIND_ONE,
  CONVERSATION_CREATE, CONVERSATION_DELETE,
  MESSAGE_CREATE,
} from '@cdm/shared';
import type {
  IdentityPayload,
  CreateConversationPayload,
  ConversationIdPayload,
  CreateMessagePayload,
} from '@cdm/shared';

@Controller()
export class ConversationController {
  constructor(private readonly service: ConversationService) {}

  @MessagePattern({ cmd: CONVERSATION_FIND_ALL })
  findAll(@Payload() identity: IdentityPayload) {
    return this.service.findAll(identity.tenantId, identity.userId);
  }

  @MessagePattern({ cmd: CONVERSATION_FIND_ONE })
  findOne(@Payload() payload: ConversationIdPayload) {
    return this.service.findOne(payload.id, payload.identity.tenantId, payload.identity.userId);
  }

  @MessagePattern({ cmd: CONVERSATION_CREATE })
  create(@Payload() payload: CreateConversationPayload) {
    return this.service.create(
      payload.identity.tenantId,
      payload.identity.orgId,
      payload.identity.userId,
      payload.kbId,
      payload.title,
    );
  }

  @MessagePattern({ cmd: CONVERSATION_DELETE })
  delete(@Payload() payload: ConversationIdPayload) {
    return this.service.delete(payload.id, payload.identity.tenantId, payload.identity.userId);
  }

  @MessagePattern({ cmd: MESSAGE_CREATE })
  createMessage(@Payload() payload: CreateMessagePayload) {
    return this.service.createMessage(
      payload.conversationId,
      payload.role,
      payload.content,
      payload.citations,
      payload.metadata,
      payload.tokenCount,
    );
  }
}
