package com.cdm.patient.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreatePatientFamilyLinkDto {
    @NotBlank(message = "家属用户ID不能为空")
    private String familyUserId;
    
    @NotBlank(message = "关系不能为空")
    private String relationship;
}
