import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { KnowledgeBaseEntity } from './entities/knowledge-base.entity.js';
import { DocumentEntity } from './entities/document.entity.js';
import type {
  CreateKbData,
  SyncDocumentPayload,
  KnowledgeBaseVO,
  KnowledgeBaseStatsVO,
  DocumentVO,
  DocumentSyncResultVO,
} from '@cdm/shared';
import type { DeleteResult } from 'typeorm';

@Injectable()
export class KnowledgeService {
  constructor(
    @InjectRepository(KnowledgeBaseEntity) private kbRepo: Repository<KnowledgeBaseEntity>,
    @InjectRepository(DocumentEntity) private docRepo: Repository<DocumentEntity>
  ) {}

  async findAllKb(tenantId: string): Promise<KnowledgeBaseVO[]> {
    const entities = await this.kbRepo.find({ where: { tenantId } });
    return entities.map(KnowledgeService.toKbVO);
  }

  async createKb(tenantId: string, orgId: string, createdBy: string, data: CreateKbData): Promise<KnowledgeBaseVO> {
    const kb = this.kbRepo.create({
      tenantId, orgId, createdBy, name: data.name, description: data.description
    });
    const saved = await this.kbRepo.save(kb);
    return KnowledgeService.toKbVO(saved);
  }

  async getKbStats(kbId: string): Promise<KnowledgeBaseStatsVO> {
    const docs = await this.docRepo.count({ where: { kbId } });
    return { document_count: docs, chunk_count: 0, total_tokens: 0 };
  }

  deleteKb(id: string): Promise<DeleteResult> {
    return this.kbRepo.delete(id);
  }

  async findDocsByKb(kbId: string): Promise<DocumentVO[]> {
    const entities = await this.docRepo.find({ where: { kbId } });
    return entities.map(KnowledgeService.toDocVO);
  }

  async syncDocument(tenantId: string, orgId: string, uploaderId: string, payload: SyncDocumentPayload): Promise<DocumentSyncResultVO> {
    const doc = this.docRepo.create({
      tenantId, orgId, uploaderId,
      kbId: payload.kbId,
      fileName: payload.fileName,
      fileType: payload.fileType ?? '',
      fileSize: payload.fileSize ?? 0,
      minioUrl: payload.minioUrl
    });
    const saved = await this.docRepo.save(doc);
    return {
      ...KnowledgeService.toDocVO(saved),
      chunkCount: payload.chunkCount,
      status: payload.status,
    };
  }

  deleteDoc(id: string): Promise<DeleteResult> {
    return this.docRepo.delete(id);
  }

  static toKbVO(entity: KnowledgeBaseEntity): KnowledgeBaseVO {
    return {
      id: entity.id,
      tenantId: entity.tenantId,
      orgId: entity.orgId,
      createdBy: entity.createdBy,
      name: entity.name,
      description: entity.description,
    };
  }

  static toDocVO(entity: DocumentEntity): DocumentVO {
    return {
      id: entity.id,
      kbId: entity.kbId,
      fileName: entity.fileName,
      fileType: entity.fileType,
      fileSize: entity.fileSize,
      minioUrl: entity.minioUrl,
    };
  }
}
