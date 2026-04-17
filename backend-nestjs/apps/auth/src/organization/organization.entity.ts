import { Entity, Column, PrimaryColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('organizations')
export class OrganizationEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: string;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: string;

  @Column({ name: 'parent_id', type: 'bigint', nullable: true })
  parentId: string | null;

  @Column({ length: 255 })
  name: string;

  @Column({ length: 50 })
  code: string;

  @Column({ length: 20, default: 'active' })
  status: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
