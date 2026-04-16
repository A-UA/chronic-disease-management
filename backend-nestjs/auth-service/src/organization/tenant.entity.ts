import { Entity, Column, PrimaryColumn, CreateDateColumn } from 'typeorm';

@Entity('tenants')
export class TenantEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ length: 255 })
  name: string;

  @Column({ unique: true, length: 100 })
  slug: string;

  @Column({ name: 'plan_type', length: 50, default: 'free' })
  planType: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt: Date;
}
