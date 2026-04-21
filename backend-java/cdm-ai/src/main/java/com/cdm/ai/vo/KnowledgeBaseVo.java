package com.cdm.ai.vo;

import lombok.Data;
import lombok.Builder;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class KnowledgeBaseVo {
    private String id;
    private String tenantId;
    private String orgId;
    private String createdBy;
    private String name;
    private String description;
    private LocalDateTime createdAt;
}
