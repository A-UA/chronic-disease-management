import { Entity, Column, PrimaryColumn, CreateDateColumn, UpdateDateColumn } from 'typeorm';

@Entity('menus')
export class MenuEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'parent_id', type: 'bigint', nullable: true })
  parentId: number | null;

  @Column({ name: 'tenant_id', type: 'bigint', nullable: true })
  tenantId: number | null;

  @Column({ length: 100 })
  name: string;

  @Column({ unique: true, length: 100 })
  code: string;

  @Column({ name: 'menu_type', length: 20, default: 'page' })
  menuType: string;

  @Column({ length: 255, nullable: true })
  path: string | null;

  @Column({ length: 50, nullable: true })
  icon: string | null;

  @Column({ name: 'permission_code', length: 100, nullable: true })
  permissionCode: string | null;

  @Column({ default: 0 })
  sort: number;

  @Column({ name: 'is_visible', default: true })
  isVisible: boolean;

  @Column({ name: 'is_enabled', default: true })
  isEnabled: boolean;

  @Column({ type: 'jsonb', nullable: true })
  meta: Record<string, any> | null;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt: Date;
}
