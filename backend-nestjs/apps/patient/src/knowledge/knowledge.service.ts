import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { KnowledgeBaseEntity } from './entities/knowledge-base.entity.js';
import { DocumentEntity } from './entities/document.entity.js';

@Injectable()
export class KnowledgeService {
  constructor(
    @InjectRepository(KnowledgeBaseEntity) private kbRepo: Repository<KnowledgeBaseEntity>,
    @InjectRepository(DocumentEntity) private docRepo: Repository<DocumentEntity>
  ) {}

  findAllKb(tenantId: number) {
    return this.kbRepo.find({ where: { tenantId } });
  }

  createKb(tenantId: number, orgId: number, createdBy: number, data: any) {
    const kb = this.kbRepo.create({
      tenantId, orgId, createdBy, name: data.name, description: data.description
    });
    return this.kbRepo.save(kb);
  }

  async getKbStats(kbId: number) {
    const docs = await this.docRepo.count({ where: { kbId } });
    return { document_count: docs, chunk_count: 0, total_tokens: 0 };
  }

  deleteKb(id: number) {
    return this.kbRepo.delete(id);
  }

  findDocsByKb(kbId: number) {
    return this.docRepo.find({ where: { kbId } });
  }

  syncDocument(tenantId: number, orgId: number, uploaderId: number, payload: any) {
    const doc = this.docRepo.create({
      tenantId, orgId, uploaderId,
      kbId: payload.kbId,
      fileName: payload.fileName,
      fileType: payload.fileType,
      fileSize: payload.fileSize,
      minioUrl: payload.minioUrl
    });
    return this.docRepo.save(doc)
      .then(saved => ({ ...saved, chunkCount: payload.chunkCount, status: payload.status }));
  }

  deleteDoc(id: number) {
    return this.docRepo.delete(id);
  }
}
