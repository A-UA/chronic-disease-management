import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { KnowledgeBaseEntity } from './entities/knowledge-base.entity.js';
import { DocumentEntity } from './entities/document.entity.js';
import { InfraService } from '../infra/infra.service.js';
import type {
  CreateKbData,
  SyncDocumentPayload,
  KnowledgeBaseVO,
  KnowledgeBaseStatsVO,
  DocumentVO,
  DocumentSyncResultVO,
  KbOwnershipResultVO,
} from '@cdm/shared';

@Injectable()
export class KnowledgeService {
  constructor(
    @InjectRepository(KnowledgeBaseEntity) private kbRepo: Repository<KnowledgeBaseEntity>,
    @InjectRepository(DocumentEntity) private docRepo: Repository<DocumentEntity>,
    private readonly infraService: InfraService,
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

  /**
   * 删除知识库（全生命周期清理）
   * 1. Agent: 清理该知识库的全部向量
   * 2. MinIO: 删除该知识库所有文档的原始文件
   * 3. DB: 删除知识库记录（CASCADE 级联删文档记录）
   */
  async deleteKb(id: string, tenantId: string): Promise<{ affected: number }> {
    // 校验归属
    const kb = await this.kbRepo.findOne({ where: { id, tenantId } });
    if (!kb) {
      return { affected: 0 };
    }

    // 1. Agent: 清理向量
    await this.infraService.deleteVectorsByKb(id);

    // 2. MinIO: 批量删除该 KB 下所有文档文件
    const docs = await this.docRepo.find({ where: { kbId: id } });
    await Promise.all(
      docs
        .filter((d) => d.minioUrl)
        .map((d) => this.infraService.deleteFile(d.minioUrl)),
    );

    // 3. DB: CASCADE 删除知识库 + 关联文档记录
    const result = await this.kbRepo.delete(id);
    return { affected: result.affected ?? 0 };
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

  /**
   * 删除文档（全生命周期清理）
   * 1. Agent: 清理该文档的向量
   * 2. MinIO: 删除原始文件
   * 3. DB: 删除文档记录
   */
  async deleteDoc(id: string): Promise<{ affected: number }> {
    const doc = await this.docRepo.findOne({ where: { id } });
    if (!doc) {
      return { affected: 0 };
    }

    // 1. Agent: 删除文档向量
    await this.infraService.deleteVectorsByDoc(doc.kbId, doc.fileName);

    // 2. MinIO: 删除原始文件
    if (doc.minioUrl) {
      await this.infraService.deleteFile(doc.minioUrl);
    }

    // 3. DB: 删除文档记录
    const result = await this.docRepo.delete(id);
    return { affected: result.affected ?? 0 };
  }

  async findOneDoc(id: string): Promise<DocumentVO | null> {
    const doc = await this.docRepo.findOne({ where: { id } });
    return doc ? KnowledgeService.toDocVO(doc) : null;
  }

  async verifyKbOwnership(kbId: string, tenantId: string): Promise<KbOwnershipResultVO> {
    const kb = await this.kbRepo.findOne({ where: { id: kbId, tenantId } });
    return { valid: !!kb, kbId, tenantId };
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
