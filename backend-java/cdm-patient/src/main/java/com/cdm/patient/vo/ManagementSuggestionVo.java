package com.cdm.patient.vo;

import lombok.Data;
import lombok.Builder;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ManagementSuggestionVo {
    private Long id;
    private Long tenantId;
    private Long orgId;
    private Long patientId;
    private Long createdByUserId;
    private String suggestionType;
    private String content;
    private String status;
    private LocalDateTime createdAt;
}
