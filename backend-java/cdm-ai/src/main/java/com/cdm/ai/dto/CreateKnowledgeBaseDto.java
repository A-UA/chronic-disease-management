package com.cdm.ai.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class CreateKnowledgeBaseDto {
    @NotBlank(message = "知识库名称不能为空")
    private String name;
    
    private String description;
}
