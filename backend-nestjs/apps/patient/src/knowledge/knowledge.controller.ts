import { Controller } from '@nestjs/common';
import { MessagePattern, Payload } from '@nestjs/microservices';
import { KnowledgeService } from './knowledge.service.js';
import {
  KNOWLEDGE_BASE_FIND_ALL, KNOWLEDGE_BASE_CREATE, KNOWLEDGE_BASE_STATS, KNOWLEDGE_BASE_DELETE,
  DOCUMENT_FIND_BY_KB, DOCUMENT_CREATE_SYNC, DOCUMENT_DELETE
} from '@cdm/shared';
import type {
  IdentityPayload,
  CreateKbPayload,
  KbIdPayload,
  DocsByKbPayload,
  SyncDocumentPayload,
  DeleteDocPayload,
} from '@cdm/shared';

@Controller()
export class KnowledgeController {
  constructor(private readonly service: KnowledgeService) {}

  @MessagePattern({ cmd: KNOWLEDGE_BASE_FIND_ALL })
  findAllKb(@Payload() identity: IdentityPayload) {
    return this.service.findAllKb(identity.tenantId);
  }

  @MessagePattern({ cmd: KNOWLEDGE_BASE_CREATE })
  createKb(@Payload() data: CreateKbPayload) {
    return this.service.createKb(data.identity.tenantId, data.identity.orgId, data.identity.userId, data.data);
  }

  @MessagePattern({ cmd: KNOWLEDGE_BASE_STATS })
  kbStats(@Payload() payload: KbIdPayload) {
    return this.service.getKbStats(payload.id);
  }

  @MessagePattern({ cmd: KNOWLEDGE_BASE_DELETE })
  deleteKb(@Payload() payload: KbIdPayload) {
    return this.service.deleteKb(payload.id);
  }

  @MessagePattern({ cmd: DOCUMENT_FIND_BY_KB })
  findDocs(@Payload() payload: DocsByKbPayload) {
    return this.service.findDocsByKb(payload.kbId);
  }

  @MessagePattern({ cmd: DOCUMENT_CREATE_SYNC })
  syncDoc(@Payload() payload: SyncDocumentPayload) {
    return this.service.syncDocument(
      payload.identity.tenantId, payload.identity.orgId, payload.identity.userId, payload
    );
  }

  @MessagePattern({ cmd: DOCUMENT_DELETE })
  deleteDoc(@Payload() payload: DeleteDocPayload) {
    return this.service.deleteDoc(payload.id);
  }
}
