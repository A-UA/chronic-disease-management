import { Controller, Get, Post, Delete, Param, UseGuards, Inject, UseInterceptors, UploadedFile } from '@nestjs/common';
import { FileInterceptor } from '@nestjs/platform-express';
import { ClientProxy } from '@nestjs/microservices';
import {
  AI_SERVICE, IdentityPayload,
  DOCUMENT_FIND_BY_KB, DOCUMENT_CREATE_SYNC, DOCUMENT_DELETE, DOCUMENT_FIND_ONE
} from '@cdm/shared';
import type { DocumentVO } from '@cdm/shared';
import { JwtAuthGuard } from '../guards/jwt-auth.guard.js';
import { CurrentUser } from '../decorators/current-user.decorator.js';
import { MinioProxyService } from './services/minio-proxy.service.js';
import { AgentProxyService } from './services/agent-proxy.service.js';
import { lastValueFrom } from 'rxjs';

@Controller('documents')
@UseGuards(JwtAuthGuard)
export class KnowledgeDocumentProxyController {
  constructor(
    @Inject(AI_SERVICE) private readonly aiClient: ClientProxy,
    private readonly minioService: MinioProxyService,
    private readonly agentService: AgentProxyService
  ) {}

  @Get('kb/:kbId/documents')
  findAll(@CurrentUser() identity: IdentityPayload, @Param('kbId') kbId: string) {
    return this.aiClient.send({ cmd: DOCUMENT_FIND_BY_KB }, { identity, kbId: Number(kbId) });
  }

  @Post('kb/:kbId/documents')
  @UseInterceptors(FileInterceptor('file'))
  async upload(
    @CurrentUser() identity: IdentityPayload,
    @Param('kbId') kbId: string,
    @UploadedFile() file: Express.Multer.File
  ) {
    const minioUrl = await this.minioService.uploadFile(file);
    const chunkCount = await this.agentService.parseDocument(file, kbId);

    const payload = {
      identity,
      kbId: Number(kbId),
      fileName: file.originalname,
      fileType: file.mimetype,
      fileSize: file.size,
      minioUrl,
      chunkCount,
      status: chunkCount > 0 ? 'completed' : 'failed'
    };

    return lastValueFrom(this.aiClient.send({ cmd: DOCUMENT_CREATE_SYNC }, payload));
  }

  @Delete(':id')
  async deleteDocument(@CurrentUser() identity: IdentityPayload, @Param('id') id: string) {
    // 1. 获取文档详情（kb_id, fileName, minioUrl）
    const doc = await lastValueFrom(
      this.aiClient.send<DocumentVO | null>({ cmd: DOCUMENT_FIND_ONE }, { id: Number(id) }),
    );

    if (doc) {
      // 2. Agent: 删除文档向量
      await this.agentService.deleteVectorsByDoc(
        String(doc.kbId),
        doc.fileName,
      );

      // 3. MinIO: 删除原始文件
      if (doc.minioUrl) {
        await this.minioService.deleteFile(doc.minioUrl);
      }
    }

    // 4. ai-service: 删除数据库记录
    return lastValueFrom(
      this.aiClient.send({ cmd: DOCUMENT_DELETE }, { identity, id: Number(id) }),
    );
  }
}
