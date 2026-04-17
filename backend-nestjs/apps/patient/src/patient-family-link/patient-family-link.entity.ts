import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('patient_family_links')
export class PatientFamilyLinkEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @Column({ name: 'patient_id', type: 'bigint' })
  patientId: number;

  @Column({ name: 'family_user_id', type: 'bigint' })
  familyUserId: number;

  @Column()
  relationship: string;

  @Column({ name: 'created_at', type: 'timestamp' })
  createdAt: Date;
}
