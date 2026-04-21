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
    private String id;
    private String tenantId;
    private String orgId;
    private String patientId;
    private String managerUserId;
    private String assignmentType;
    private LocalDateTime createdAt;
}
