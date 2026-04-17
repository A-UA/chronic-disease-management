import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('patient_manager_assignments')
export class ManagerAssignmentEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: string;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: string;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: string;

  @Column({ name: 'patient_id', type: 'bigint' })
  patientId: string;

  @Column({ name: 'manager_user_id', type: 'bigint' })
  managerUserId: string;

  @Column({ name: 'assignment_type' })
  assignmentType: string;

  @Column({ name: 'created_at', type: 'timestamp' })
  createdAt: Date;
}
