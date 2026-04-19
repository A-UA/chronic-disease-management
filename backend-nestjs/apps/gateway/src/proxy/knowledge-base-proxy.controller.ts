import { Controller, Get, Post, Delete, Param, Body, UseGuards, Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import {
  AI_SERVICE, KNOWLEDGE_BASE_FIND_ALL,
  KNOWLEDGE_BASE_CREATE, KNOWLEDGE_BASE_STATS, KNOWLEDGE_BASE_DELETE
} from '@cdm/shared';
import type { IdentityPayload } from '@cdm/shared';
import { CreateKbDto } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';
import { CurrentUser } from '../decorators/current-user.decorator.js';
import { AgentProxyService } from './services/agent-proxy.service.js';
import { lastValueFrom } from 'rxjs';

@Controller('kb')
@UseGuards(JwtAuthGuard)
export class KnowledgeBaseProxyController {
  constructor(
    @Inject(AI_SERVICE) private readonly aiClient: ClientProxy,
    private readonly agentService: AgentProxyService,
  ) {}

  @Get()
  findAll(@CurrentUser() identity: IdentityPayload) {
    return this.aiClient.send({ cmd: KNOWLEDGE_BASE_FIND_ALL }, identity);
  }

  @Post()
  create(@CurrentUser() identity: IdentityPayload, @Body() data: CreateKbDto) {
    return this.aiClient.send({ cmd: KNOWLEDGE_BASE_CREATE }, { identity, data });
  }

  @Get(':id/stats')
  stats(@CurrentUser() identity: IdentityPayload, @Param('id') id: string) {
    return this.aiClient.send({ cmd: KNOWLEDGE_BASE_STATS }, { identity, id });
  }

  @Delete(':id')
  async deleteKb(@CurrentUser() identity: IdentityPayload, @Param('id') id: string) {
    // 1. Agent: 清理该知识库的全部向量
    await this.agentService.deleteVectorsByKb(id);

    // 2. ai-service: 删除知识库记录（CASCADE 自动删关联文档记录）
    return lastValueFrom(
      this.aiClient.send({ cmd: KNOWLEDGE_BASE_DELETE }, { identity, id }),
    );
  }
}
