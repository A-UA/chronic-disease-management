import { Entity, Column, PrimaryGeneratedColumn } from 'typeorm';

@Entity('documents')
export class DocumentEntity {
  @PrimaryGeneratedColumn({ type: 'bigint' })
  id: string;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: string;

  @Column({ name: 'kb_id', type: 'bigint' })
  kbId: string;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: string;

  @Column({ name: 'uploader_id', type: 'bigint' })
  uploaderId: string;

  @Column({ name: 'file_name' })
  fileName: string;

  @Column({ name: 'file_type', nullable: true })
  fileType: string;

  @Column({ name: 'file_size', nullable: true })
  fileSize: number;

  @Column({ name: 'minio_url' })
  minioUrl: string;
}
