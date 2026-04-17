import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('management_suggestions')
export class ManagementSuggestionEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: string;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: string;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: string;

  @Column({ name: 'patient_id', type: 'bigint' })
  patientId: string;

  @Column({ name: 'created_by_user_id', type: 'bigint' })
  createdByUserId: string;

  @Column({ name: 'suggestion_type' })
  suggestionType: string;

  @Column({ name: 'content' })
  content: string;

  @Column({ name: 'status' })
  status: string;

  @Column({ name: 'created_at', type: 'timestamp' })
  createdAt: Date;
}
