package com.cdm.patient.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.cdm.common.domain.BaseEntity;
import com.cdm.patient.vo.PatientFamilyLinkVo;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@TableName("patient_family_links")
@Getter
@Setter
@NoArgsConstructor
public class PatientFamilyLinkEntity extends BaseEntity {

    private Long tenantId;
    private Long orgId;
    private Long patientId;
    private Long familyUserId;
    private String relationship;
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
