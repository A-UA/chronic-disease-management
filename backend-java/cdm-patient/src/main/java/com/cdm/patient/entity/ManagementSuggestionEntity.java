package com.cdm.patient.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.cdm.common.domain.BaseEntity;
import com.cdm.patient.vo.ManagementSuggestionVo;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@TableName("management_suggestions")
@Getter
@Setter
@NoArgsConstructor
public class ManagementSuggestionEntity extends BaseEntity {

    private Long tenantId;
    private Long orgId;
    private Long patientId;
    private Long createdByUserId;
    private String suggestionType;
    private String content;
    private String status;
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
