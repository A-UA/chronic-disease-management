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
    private Long id;
    private Long tenantId;
    private Long orgId;
    private Long createdBy;
    private String name;
    private String description;
    private LocalDateTime createdAt;
}
