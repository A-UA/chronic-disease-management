package com.cdm.patient.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class CreatePatientFamilyLinkDto {
    @NotNull(message = "家属用户ID不能为空")
    private Long familyUserId;
    
    @NotBlank(message = "关系不能为空")
    private String relationship;
}
