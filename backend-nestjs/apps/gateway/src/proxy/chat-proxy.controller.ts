import { Controller, Get, Post, Delete, Param, Body, UseGuards, Inject, Res } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import { Response } from 'express';
import { lastValueFrom } from 'rxjs';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';
import { CurrentUser } from '../decorators/current-user.decorator.js';
import {
  AI_SERVICE, IdentityPayload,
  CONVERSATION_FIND_ALL, CONVERSATION_FIND_ONE,
  CONVERSATION_CREATE, CONVERSATION_DELETE,
  KB_VERIFY_OWNERSHIP,
} from '@cdm/shared';
import type { KbOwnershipResultVO, ConversationVO, ChatRequestDto } from '@cdm/shared';
import { AgentProxyService } from './services/agent-proxy.service.js';

@Controller('conversations')
@UseGuards(JwtAuthGuard)
export class ConversationProxyController {
  constructor(@Inject(AI_SERVICE) private readonly aiClient: ClientProxy) {}

  @Get()
  findAll(@CurrentUser() identity: IdentityPayload) {
    return this.aiClient.send({ cmd: CONVERSATION_FIND_ALL }, identity);
  }

  @Get(':id')
  findOne(@CurrentUser() identity: IdentityPayload, @Param('id') id: string) {
    return this.aiClient.send({ cmd: CONVERSATION_FIND_ONE }, { identity, id });
  }

  @Delete(':id')
  delete(@CurrentUser() identity: IdentityPayload, @Param('id') id: string) {
    return this.aiClient.send({ cmd: CONVERSATION_DELETE }, { identity, id });
  }
}

@Controller('chat')
@UseGuards(JwtAuthGuard)
export class ChatProxyController {
  constructor(
    @Inject(AI_SERVICE) private readonly aiClient: ClientProxy,
    private readonly agentService: AgentProxyService,
  ) {}

  @Post()
  async sendChat(
    @Body() body: ChatRequestDto,
    @CurrentUser() identity: IdentityPayload,
    @Res() res: Response,
  ) {
    // 1. 验证 kbId 归属当前租户
    const ownership = await lastValueFrom(
      this.aiClient.send<KbOwnershipResultVO>({ cmd: KB_VERIFY_OWNERSHIP }, {
        kbId: body.kbId,
        tenantId: identity.tenantId,
      }),
    );
    if (!ownership.valid) {
      res.status(403).json({ message: 'Knowledge base not accessible' });
      return;
    }

    // 2. 如果没有 conversationId，自动创建会话
    let conversationId = body.conversationId;
    if (!conversationId) {
      const conv = await lastValueFrom(
        this.aiClient.send<ConversationVO>({ cmd: CONVERSATION_CREATE }, {
          identity,
          kbId: body.kbId,
          title: body.query.slice(0, 50),
        }),
      );
      conversationId = conv.id;
    }

    // 3. 调用 AgentProxyService 流式聊天
    await this.agentService.streamChat(
      identity,
      body.query,
      body.kbId,
      conversationId,
      this.aiClient,
      res,
    );
  }
}
