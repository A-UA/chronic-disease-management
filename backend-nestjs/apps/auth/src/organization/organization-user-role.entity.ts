import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('organization_user_roles')
export class OrganizationUserRoleEntity {
  @PrimaryColumn({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @PrimaryColumn({ name: 'user_id', type: 'bigint' })
  userId: number;

  @PrimaryColumn({ name: 'role_id', type: 'bigint' })
  roleId: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;
}
