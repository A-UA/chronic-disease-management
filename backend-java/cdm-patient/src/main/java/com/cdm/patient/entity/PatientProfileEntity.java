package com.cdm.patient.entity;

import com.cdm.common.domain.BaseEntity;
import com.cdm.patient.vo.PatientVo;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "patient_profiles")
@Getter
@Setter
@NoArgsConstructor
public class PatientProfileEntity extends BaseEntity {

    @Column(name = "tenant_id")
    private String tenantId;
    
    @Column(name = "org_id")
    private String orgId;
    
    private String name;
    private String gender;

    public static PatientVo toVo(PatientProfileEntity entity) {
        if (entity == null) return null;
        return PatientVo.builder()
                .id(entity.getId())
                .tenantId(entity.getTenantId())
                .orgId(entity.getOrgId())
                .name(entity.getName())
                .gender(entity.getGender())
                .build();
    }
}
