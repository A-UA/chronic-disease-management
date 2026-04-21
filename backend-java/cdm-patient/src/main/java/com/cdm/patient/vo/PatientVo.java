package com.cdm.patient.vo;

import lombok.Data;
import lombok.Builder;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PatientVo {
    private String id;
    private String tenantId;
    private String orgId;
    private String name;
    private String gender;
}
