import { Entity, Column, PrimaryGeneratedColumn } from 'typeorm';

@Entity('knowledge_bases')
export class KnowledgeBaseEntity {
  @PrimaryGeneratedColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @Column({ name: 'created_by', type: 'bigint' })
  createdBy: number;

  @Column()
  name: string;

  @Column({ nullable: true })
  description: string;
}
