import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { KnowledgeBaseEntity } from './entities/knowledge-base.entity.js';
import { DocumentEntity } from './entities/document.entity.js';
import type { CreateKbData, SyncDocumentPayload } from '@cdm/shared';

@Injectable()
export class KnowledgeService {
  constructor(
    @InjectRepository(KnowledgeBaseEntity) private kbRepo: Repository<KnowledgeBaseEntity>,
    @InjectRepository(DocumentEntity) private docRepo: Repository<DocumentEntity>
  ) {}

  findAllKb(tenantId: string) {
    return this.kbRepo.find({ where: { tenantId } });
  }

  createKb(tenantId: string, orgId: string, createdBy: string, data: CreateKbData) {
    const kb = this.kbRepo.create({
      tenantId, orgId, createdBy, name: data.name, description: data.description
    });
    return this.kbRepo.save(kb);
  }

  async getKbStats(kbId: string) {
    const docs = await this.docRepo.count({ where: { kbId } });
    return { document_count: docs, chunk_count: 0, total_tokens: 0 };
  }

  deleteKb(id: string) {
    return this.kbRepo.delete(id);
  }

  findDocsByKb(kbId: string) {
    return this.docRepo.find({ where: { kbId } });
  }

  syncDocument(tenantId: string, orgId: string, uploaderId: string, payload: SyncDocumentPayload) {
    const doc = this.docRepo.create({
      tenantId, orgId, uploaderId,
      kbId: payload.kbId,
      fileName: payload.fileName,
      fileType: payload.fileType ?? '',
      fileSize: payload.fileSize ?? 0,
      minioUrl: payload.minioUrl
    });
    return this.docRepo.save(doc)
      .then(saved => ({ ...saved, chunkCount: payload.chunkCount, status: payload.status }));
  }

  deleteDoc(id: string) {
    return this.docRepo.delete(id);
  }
}
