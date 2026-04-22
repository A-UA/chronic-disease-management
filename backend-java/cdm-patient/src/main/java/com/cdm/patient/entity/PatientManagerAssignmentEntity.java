package com.cdm.patient.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.cdm.common.domain.BaseEntity;
import com.cdm.patient.vo.PatientManagerAssignmentVo;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@TableName("patient_manager_assignments")
@Getter
@Setter
@NoArgsConstructor
public class PatientManagerAssignmentEntity extends BaseEntity {

    private Long tenantId;
    private Long orgId;
    private Long patientId;
    private Long managerUserId;
    private String assignmentType;
    private LocalDateTime createdAt;

    public static PatientManagerAssignmentVo toVo(PatientManagerAssignmentEntity entity) {
        if (entity == null) return null;
        return PatientManagerAssignmentVo.builder()
                .id(entity.getId())
                .tenantId(entity.getTenantId())
                .orgId(entity.getOrgId())
                .patientId(entity.getPatientId())
                .managerUserId(entity.getManagerUserId())
                .assignmentType(entity.getAssignmentType())
                .createdAt(entity.getCreatedAt())
                .build();
    }
}
