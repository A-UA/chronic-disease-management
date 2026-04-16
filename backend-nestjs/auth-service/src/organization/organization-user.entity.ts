import { Entity, Column, PrimaryColumn, CreateDateColumn } from 'typeorm';

@Entity('organization_users')
export class OrganizationUserEntity {
  @PrimaryColumn({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @PrimaryColumn({ name: 'user_id', type: 'bigint' })
  userId: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;

  @Column({ name: 'user_type', length: 20, default: 'staff' })
  userType: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
