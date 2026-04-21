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
    private String id;
    private String tenantId;
    private String kbId;
    private String orgId;
    private String uploaderId;
    private String fileName;
    private String fileType;
    private Integer fileSize;
    private String minioUrl;
    private String status;
    private Integer chunkCount;
    private LocalDateTime updatedAt;
    private LocalDateTime createdAt;
}
