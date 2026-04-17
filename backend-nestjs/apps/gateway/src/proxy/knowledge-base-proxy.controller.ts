import { Controller, Get, Post, Delete, Param, Body, UseGuards, Inject } from '@nestjs/common';
import { ClientProxy } from '@nestjs/microservices';
import {
  PATIENT_SERVICE, KNOWLEDGE_BASE_FIND_ALL,
  KNOWLEDGE_BASE_CREATE, KNOWLEDGE_BASE_STATS, KNOWLEDGE_BASE_DELETE
} from '@cdm/shared';
import type { IdentityPayload } from '@cdm/shared';
import { CreateKbDto } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';
import { CurrentUser } from '../decorators/current-user.decorator.js';

@Controller('kb')
@UseGuards(JwtAuthGuard)
export class KnowledgeBaseProxyController {
  constructor(@Inject(PATIENT_SERVICE) private readonly patientClient: ClientProxy) {}

  @Get()
  findAll(@CurrentUser() identity: IdentityPayload) {
    return this.patientClient.send({ cmd: KNOWLEDGE_BASE_FIND_ALL }, identity);
  }

  @Post()
  create(@CurrentUser() identity: IdentityPayload, @Body() data: CreateKbDto) {
    return this.patientClient.send({ cmd: KNOWLEDGE_BASE_CREATE }, { identity, data });
  }

  @Get(':id/stats')
  stats(@CurrentUser() identity: IdentityPayload, @Param('id') id: string) {
    return this.patientClient.send({ cmd: KNOWLEDGE_BASE_STATS }, { identity, id });
  }

  @Delete(':id')
  deleteKb(@CurrentUser() identity: IdentityPayload, @Param('id') id: string) {
    return this.patientClient.send({ cmd: KNOWLEDGE_BASE_DELETE }, { identity, id });
  }
}
