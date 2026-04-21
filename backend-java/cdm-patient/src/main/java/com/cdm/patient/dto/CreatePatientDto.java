package com.cdm.patient.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreatePatientDto {
    @NotBlank(message = "姓名不能为空")
    private String name;
    
    @NotBlank(message = "性别不能为空")
    private String gender;
}
