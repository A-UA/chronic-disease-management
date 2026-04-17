import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('patient_manager_assignments')
export class ManagerAssignmentEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @Column({ name: 'patient_id', type: 'bigint' })
  patientId: number;

  @Column({ name: 'manager_user_id', type: 'bigint' })
  managerUserId: number;

  @Column({ name: 'assignment_type' })
  assignmentType: string;

  @Column({ name: 'created_at', type: 'timestamp' })
  createdAt: Date;
}
