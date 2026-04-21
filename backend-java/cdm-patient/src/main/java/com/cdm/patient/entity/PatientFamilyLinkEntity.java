package com.cdm.patient.entity;

import com.cdm.common.domain.BaseEntity;
import com.cdm.patient.vo.PatientFamilyLinkVo;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Entity
@Table(name = "patient_family_links")
@Getter
@Setter
@NoArgsConstructor
public class PatientFamilyLinkEntity extends BaseEntity {

    @Column(name = "tenant_id")
    private String tenantId;

    @Column(name = "org_id")
    private String orgId;

    @Column(name = "patient_id")
    private String patientId;

    @Column(name = "family_user_id")
    private String familyUserId;

    @Column(name = "relationship")
    private String relationship;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public static PatientFamilyLinkVo toVo(PatientFamilyLinkEntity entity) {
        if (entity == null) return null;
        return PatientFamilyLinkVo.builder()
                .id(entity.getId())
                .tenantId(entity.getTenantId())
                .orgId(entity.getOrgId())
                .patientId(entity.getPatientId())
                .familyUserId(entity.getFamilyUserId())
                .relationship(entity.getRelationship())
                .createdAt(entity.getCreatedAt())
                .build();
    }
}
