package com.cdm.patient.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CreatePatientManagerAssignmentDto {
    @NotNull(message = "管理人ID不能为空")
    private Long managerUserId;
    
    @NotBlank(message = "管理关系类型不能为空")
    private String assignmentType;
}
