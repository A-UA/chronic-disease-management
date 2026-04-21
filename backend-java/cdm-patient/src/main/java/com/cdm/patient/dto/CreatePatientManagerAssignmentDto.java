package com.cdm.patient.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreatePatientManagerAssignmentDto {
    @NotBlank(message = "管理人ID不能为空")
    private String managerUserId;
    
    @NotBlank(message = "管理关系类型不能为空")
    private String assignmentType;
}
