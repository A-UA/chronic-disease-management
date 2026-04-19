import { Injectable, OnModuleInit } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import * as Minio from 'minio';

/**
 * Agent HTTP 调用 + MinIO 文件操作
 * 集中管理 ai-service 对外部服务的依赖
 */
@Injectable()
export class InfraService implements OnModuleInit {
  private agentUrl = process.env.AGENT_URL || 'http://localhost:8000';
  private minioClient!: Minio.Client;
  private bucketName = process.env.MINIO_BUCKET || 'cdm-docs';
  private minioEndpoint = process.env.MINIO_ENDPOINT || 'localhost';
  private minioPort = Number(process.env.MINIO_PORT) || 9000;

  constructor(private readonly httpService: HttpService) {}

  onModuleInit() {
    this.minioClient = new Minio.Client({
      endPoint: this.minioEndpoint,
      port: this.minioPort,
      useSSL: false,
      accessKey: process.env.MINIO_ACCESS_KEY || 'minioadmin',
      secretKey: process.env.MINIO_SECRET_KEY || 'minioadmin',
    });
  }

  // ─── Agent 向量操作 ───

  /** 删除整个知识库的向量 */
  async deleteVectorsByKb(kbId: string): Promise<number> {
    try {
      const response = await this.httpService.axiosRef.delete<{ deleted_count: number }>(
        `${this.agentUrl}/internal/knowledge/vectors/kb/${kbId}`,
      );
      return response.data?.deleted_count ?? 0;
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      console.error('[InfraService] deleteVectorsByKb failed:', message);
      return 0;
    }
  }

  /** 删除指定文档的向量 */
  async deleteVectorsByDoc(kbId: string, filename: string): Promise<number> {
    try {
      const response = await this.httpService.axiosRef.delete<{ deleted_count: number }>(
        `${this.agentUrl}/internal/knowledge/vectors/kb/${kbId}/doc/${encodeURIComponent(filename)}`,
      );
      return response.data?.deleted_count ?? 0;
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : 'Unknown error';
      console.error('[InfraService] deleteVectorsByDoc failed:', message);
      return 0;
    }
  }

  // ─── MinIO 文件操作 ───

  /** 根据完整 MinIO URL 删除对象 */
  async deleteFile(minioUrl: string): Promise<void> {
    try {
      const urlObj = new URL(minioUrl);
      const pathParts = urlObj.pathname.split('/').filter(Boolean);
      if (pathParts.length >= 2) {
        const objectName = pathParts.slice(1).join('/');
        await this.minioClient.removeObject(this.bucketName, objectName);
      }
    } catch (err: unknown) {
      console.error('[InfraService] deleteFile failed:', err instanceof Error ? err.message : err);
    }
  }
}
