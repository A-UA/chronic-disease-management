package com.cdm.ai.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.annotation.TableField;
import com.cdm.common.domain.BaseEntity;
import com.cdm.ai.vo.DocumentVo;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@TableName("documents")
@Getter
@Setter
@NoArgsConstructor
public class DocumentEntity extends BaseEntity {

    private Long tenantId;
    private Long kbId;
    private Long orgId;
    private Long uploaderId;
    private String fileName;
    private String fileType;
    private Integer fileSize;
    private String minioUrl;
    private LocalDateTime updatedAt;

    @TableField(exist = false)
    private String status = "completed"; 
    
    @TableField(exist = false)
    private Integer chunkCount = 0;

    public static DocumentVo toVo(DocumentEntity entity) {
        if (entity == null) return null;
        return DocumentVo.builder()
                .id(entity.getId())
                .tenantId(entity.getTenantId())
                .kbId(entity.getKbId())
                .orgId(entity.getOrgId())
                .uploaderId(entity.getUploaderId())
                .fileName(entity.getFileName())
                .fileType(entity.getFileType())
                .fileSize(entity.getFileSize())
                .minioUrl(entity.getMinioUrl())
                .status(entity.getStatus())
                .chunkCount(entity.getChunkCount())
                .updatedAt(entity.getUpdatedAt())
                .createdAt(entity.getCreatedAt())
                .build();
    }
}
