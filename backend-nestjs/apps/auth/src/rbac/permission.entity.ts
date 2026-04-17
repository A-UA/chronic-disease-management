import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('permissions')
export class PermissionEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: string;

  @Column({ length: 100 })
  name: string;

  @Column({ unique: true, length: 100 })
  code: string;

  @Column({ name: 'resource_id', type: 'bigint' })
  resourceId: string;

  @Column({ name: 'action_id', type: 'bigint' })
  actionId: string;
}
