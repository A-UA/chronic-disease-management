import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('management_suggestions')
export class ManagementSuggestionEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @Column({ name: 'patient_id', type: 'bigint' })
  patientId: number;

  @Column({ name: 'created_by_user_id', type: 'bigint' })
  createdByUserId: number;

  @Column({ name: 'suggestion_type' })
  suggestionType: string;

  @Column({ name: 'content' })
  content: string;

  @Column({ name: 'status' })
  status: string;

  @Column({ name: 'created_at', type: 'timestamp' })
  createdAt: Date;
}
