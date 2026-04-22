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
public class DocumentVo {
    private Long id;
    private Long tenantId;
    private Long kbId;
    private Long orgId;
    private Long uploaderId;
    private String fileName;
    private String fileType;
    private Integer fileSize;
    private String minioUrl;
    private String status;
    private Integer chunkCount;
    private LocalDateTime updatedAt;
    private LocalDateTime createdAt;
}
