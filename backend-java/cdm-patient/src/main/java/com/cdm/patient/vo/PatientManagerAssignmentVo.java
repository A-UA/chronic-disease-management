package com.cdm.patient.vo;

import lombok.Data;
import lombok.Builder;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class PatientManagerAssignmentVo {
    private Long id;
    private Long tenantId;
    private Long orgId;
    private Long patientId;
    private Long managerUserId;
    private String assignmentType;
    private LocalDateTime createdAt;
}
