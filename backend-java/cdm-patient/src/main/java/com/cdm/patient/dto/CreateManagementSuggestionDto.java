package com.cdm.patient.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateManagementSuggestionDto {
    @NotBlank(message = "建议类型不能为空")
    private String suggestionType;
    
    @NotBlank(message = "建议内容不能为空")
    private String content;
}
