import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('patient_family_links')
export class PatientFamilyLinkEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: string;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: string;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: string;

  @Column({ name: 'patient_id', type: 'bigint' })
  patientId: string;

  @Column({ name: 'family_user_id', type: 'bigint' })
  familyUserId: string;

  @Column()
  relationship: string;

  @Column({ name: 'created_at', type: 'timestamp' })
  createdAt: Date;
}
