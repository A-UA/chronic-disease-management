import { Injectable, OnModuleInit } from '@nestjs/common';
import * as Minio from 'minio';
import { v4 as uuidv4 } from 'uuid';

@Injectable()
export class MinioProxyService implements OnModuleInit {
  private minioClient: Minio.Client;
  private bucketName = process.env.MINIO_BUCKET || 'cdm-docs';
  private endpoint = process.env.MINIO_ENDPOINT || 'localhost';
  private port = Number(process.env.MINIO_PORT) || 9000;

  onModuleInit() {
    this.minioClient = new Minio.Client({
      endPoint: this.endpoint,
      port: this.port,
      useSSL: false,
      accessKey: process.env.MINIO_ACCESS_KEY || 'minioadmin',
      secretKey: process.env.MINIO_SECRET_KEY || 'minioadmin',
    });

    this.minioClient.bucketExists(this.bucketName).then((exists) => {
      if (!exists) {
        this.minioClient.makeBucket(this.bucketName, 'us-east-1').catch(console.error);
      }
    }).catch(console.error);
  }

  async uploadFile(file: Express.Multer.File): Promise<string> {
    const filename = `${uuidv4()}_${file.originalname}`;
    await this.minioClient.putObject(
      this.bucketName,
      filename,
      file.buffer,
      file.size,
      { 'Content-Type': file.mimetype }
    );
    return `http://${this.endpoint}:${this.port}/${this.bucketName}/${filename}`;
  }

  /**
   * 根据完整 MinIO URL 删除对象
   */
  async deleteFile(minioUrl: string): Promise<void> {
    try {
      const urlObj = new URL(minioUrl);
      // 路径格式: /bucket/objectName
      const pathParts = urlObj.pathname.split('/').filter(Boolean);
      if (pathParts.length >= 2) {
        const objectName = pathParts.slice(1).join('/');
        await this.minioClient.removeObject(this.bucketName, objectName);
      }
    } catch (err) {
      console.error('MinIO delete failed:', err instanceof Error ? err.message : err);
    }
  }
}
