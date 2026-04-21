package com.cdm.patient.entity;

import com.cdm.common.domain.BaseEntity;
import com.cdm.patient.vo.ManagementSuggestionVo;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Entity
@Table(name = "management_suggestions")
@Getter
@Setter
@NoArgsConstructor
public class ManagementSuggestionEntity extends BaseEntity {

    @Column(name = "tenant_id")
    private String tenantId;

    @Column(name = "org_id")
    private String orgId;

    @Column(name = "patient_id")
    private String patientId;

    @Column(name = "created_by_user_id")
    private String createdByUserId;

    @Column(name = "suggestion_type")
    private String suggestionType;

    @Column(name = "content")
    private String content;

    @Column(name = "status")
    private String status;

    @Column(name = "created_at")
    private LocalDateTime createdAt;

    public static ManagementSuggestionVo toVo(ManagementSuggestionEntity entity) {
        if (entity == null) return null;
        return ManagementSuggestionVo.builder()
                .id(entity.getId())
                .tenantId(entity.getTenantId())
                .orgId(entity.getOrgId())
                .patientId(entity.getPatientId())
                .createdByUserId(entity.getCreatedByUserId())
                .suggestionType(entity.getSuggestionType())
                .content(entity.getContent())
                .status(entity.getStatus())
                .createdAt(entity.getCreatedAt())
                .build();
    }
}
