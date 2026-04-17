import { Controller, Get, Post, Delete, Param, Body, UseGuards, Res } from '@nestjs/common';
import { Response } from 'express';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';
import { CurrentUser } from '../decorators/current-user.decorator.js';
import { IdentityPayload } from '@cdm/shared';
import { AgentProxyService } from './services/agent-proxy.service.js';

@Controller('conversations')
@UseGuards(JwtAuthGuard)
export class ConversationProxyController {
  constructor(private readonly agentService: AgentProxyService) {}

  @Get()
  getConversations(@CurrentUser() user: IdentityPayload) {
    return this.agentService.getConversations(user.userId);
  }

  @Get(':id')
  getConversation(@Param('id') id: string, @CurrentUser() user: IdentityPayload) {
    return this.agentService.getConversation(id, user.userId);
  }

  @Delete(':id')
  deleteConversation(@Param('id') id: string, @CurrentUser() user: IdentityPayload) {
    return this.agentService.deleteConversation(id, user.userId);
  }
}

@Controller('chat')
@UseGuards(JwtAuthGuard)
export class ChatProxyController {
  constructor(private readonly agentService: AgentProxyService) {}

  @Post()
  async sendChat(
    @Body() body: { kb_id: string; query: string; conversation_id?: string },
    @CurrentUser() user: IdentityPayload,
    @Res() res: Response
  ) {
    await this.agentService.streamChat(
      user.userId,
      body.query,
      body.kb_id,
      body.conversation_id,
      res
    );
  }
}
