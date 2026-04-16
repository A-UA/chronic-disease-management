import { Entity, Column, PrimaryColumn } from 'typeorm';

@Entity('health_metrics')
export class HealthMetricEntity {
  @PrimaryColumn({ type: 'bigint' })
  id: number;

  @Column({ name: 'tenant_id', type: 'bigint' })
  tenantId: number;

  @Column({ name: 'org_id', type: 'bigint' })
  orgId: number;

  @Column({ name: 'patient_id', type: 'bigint' })
  patientId: number;

  @Column({ name: 'metric_type' })
  metricType: string;

  @Column({ name: 'metric_value' })
  metricValue: string;

  @Column({ name: 'recorded_at', type: 'timestamp' })
  recordedAt: Date;
}
