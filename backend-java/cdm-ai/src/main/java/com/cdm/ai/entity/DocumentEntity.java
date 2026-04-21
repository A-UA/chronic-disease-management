package com.cdm.ai.entity;

import com.cdm.common.domain.BaseEntity;
import com.cdm.ai.vo.DocumentVo;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import jakarta.persistence.Transient;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;

@Entity
@Table(name = "documents")
@Getter
@Setter
@NoArgsConstructor
public class DocumentEntity extends BaseEntity {

    @Column(name = "tenant_id", nullable = false)
    private String tenantId;

    @Column(name = "kb_id", nullable = false)
    private String kbId;

    @Column(name = "org_id", nullable = false)
    private String orgId;

    @Column(name = "uploader_id", nullable = false)
    private String uploaderId;

    @Column(name = "file_name", nullable = false)
    private String fileName;

    @Column(name = "file_type")
    private String fileType;

    @Column(name = "file_size")
    private Integer fileSize;

    @Column(name = "minio_url", nullable = false)
    private String minioUrl;
    
    @Column(name = "updated_at")
    private LocalDateTime updatedAt;

    @Transient
    private String status = "completed"; 
    
    @Transient
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
