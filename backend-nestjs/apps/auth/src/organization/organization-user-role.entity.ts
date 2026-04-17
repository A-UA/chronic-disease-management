import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('organization_user_roles')
export class OrganizationUserRoleEntity {
  @PrimaryColumn({ name: 'org_id', type: 'bigint' })
  orgId: string;

  @PrimaryColumn({ name: 'user_id', type: 'bigint' })
  userId: string;

  @PrimaryColumn({ name: 'role_id', type: 'bigint' })
  roleId: string;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: string;
}
