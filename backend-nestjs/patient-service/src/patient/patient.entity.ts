import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('patient_profiles')
export class PatientEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @Column()
  name: string;

  @Column()
  gender: string;
}
