package com.cdm.patient.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.cdm.common.domain.BaseEntity;
import com.cdm.patient.vo.HealthMetricVo;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@TableName("health_metrics")
@Getter
@Setter
@NoArgsConstructor
public class HealthMetricEntity extends BaseEntity {

    private Long tenantId;
    private Long orgId;
    private Long patientId;
    private String metricType;
    private String metricValue;
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
