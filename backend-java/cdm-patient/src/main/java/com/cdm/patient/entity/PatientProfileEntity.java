package com.cdm.patient.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.cdm.common.domain.BaseEntity;
import com.cdm.patient.vo.PatientVo;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;

@TableName("patient_profiles")
@Getter
@Setter
@NoArgsConstructor
public class PatientProfileEntity extends BaseEntity {

    private Long tenantId;
    private Long orgId;
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
