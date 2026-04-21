package com.cdm.patient.entity;

import com.cdm.common.domain.BaseEntity;
import com.cdm.patient.vo.HealthMetricVo;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Entity
@Table(name = "health_metrics")
@Getter
@Setter
@NoArgsConstructor
public class HealthMetricEntity extends BaseEntity {

    @Column(name = "tenant_id")
    private String tenantId;

    @Column(name = "org_id")
    private String orgId;

    @Column(name = "patient_id")
    private String patientId;

    @Column(name = "metric_type")
    private String metricType;

    @Column(name = "metric_value")
    private String metricValue;

    @Column(name = "recorded_at")
    private LocalDateTime recordedAt;

    public static HealthMetricVo toVo(HealthMetricEntity entity) {
        if (entity == null) return null;
        return HealthMetricVo.builder()
                .id(entity.getId())
                .tenantId(entity.getTenantId())
                .orgId(entity.getOrgId())
                .patientId(entity.getPatientId())
                .metricType(entity.getMetricType())
                .metricValue(entity.getMetricValue())
                .recordedAt(entity.getRecordedAt())
                .build();
    }
}
