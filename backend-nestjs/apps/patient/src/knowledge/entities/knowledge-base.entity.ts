import { Entity, Column, PrimaryGeneratedColumn } from 'typeorm';

@Entity('knowledge_bases')
export class KnowledgeBaseEntity {
  @PrimaryGeneratedColumn({ type: 'bigint' })
  id: string;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: string;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: string;

  @Column({ name: 'created_by', type: 'bigint' })
  createdBy: string;

  @Column()
  name: string;

  @Column({ nullable: true })
  description: string;
}
