import { Entity, Column, PrimaryColumn, CreateDateColumn } from 'typeorm';

@Entity('organization_users')
export class OrganizationUserEntity {
  @PrimaryColumn({ name: 'org_id', type: 'bigint' })
  orgId: string;

  @PrimaryColumn({ name: 'user_id', type: 'bigint' })
  userId: string;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: string;

  @Column({ name: 'user_type', length: 20, default: 'staff' })
  userType: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
