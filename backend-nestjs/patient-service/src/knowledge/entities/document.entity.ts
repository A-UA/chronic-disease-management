import { Entity, Column, PrimaryGeneratedColumn } from 'typeorm';

@Entity('documents')
export class DocumentEntity {
  @PrimaryGeneratedColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;

  @Column({ name: 'kb_id', type: 'bigint' })
  kbId: number;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @Column({ name: 'uploader_id', type: 'bigint' })
  uploaderId: number;

  @Column({ name: 'file_name' })
  fileName: string;

  @Column({ name: 'file_type', nullable: true })
  fileType: string;

  @Column({ name: 'file_size', nullable: true })
  fileSize: number;

  @Column({ name: 'minio_url' })
  minioUrl: string;
}
