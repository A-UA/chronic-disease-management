import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('health_metrics')
export class HealthMetricEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: string;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: string;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: string;

  @Column({ name: 'patient_id', type: 'bigint' })
  patientId: string;

  @Column({ name: 'metric_type' })
  metricType: string;

  @Column({ name: 'metric_value' })
  metricValue: string;

  @Column({ name: 'recorded_at', type: 'timestamp' })
  recordedAt: Date;
}
