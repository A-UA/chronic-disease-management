package com.cdm.patient.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateHealthMetricDto {
    @NotBlank(message = "指标类型不能为空")
    private String metricType;
    
    @NotBlank(message = "指标数值不能为空")
    private String metricValue;
}
