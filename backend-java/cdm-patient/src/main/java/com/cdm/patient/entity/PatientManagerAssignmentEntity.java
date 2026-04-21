package com.cdm.patient.entity;

import com.cdm.common.domain.BaseEntity;
import com.cdm.patient.vo.PatientManagerAssignmentVo;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Entity
@Table(name = "patient_manager_assignments")
@Getter
@Setter
@NoArgsConstructor
public class PatientManagerAssignmentEntity extends BaseEntity {

    @Column(name = "tenant_id")
    private String tenantId;

    @Column(name = "org_id")
    private String orgId;

    @Column(name = "patient_id")
    private String patientId;

    @Column(name = "manager_user_id")
    private String managerUserId;

    @Column(name = "assignment_type")
    private String assignmentType;

    @Column(name = "created_at")
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
