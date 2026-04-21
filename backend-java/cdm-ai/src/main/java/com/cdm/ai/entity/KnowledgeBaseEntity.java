package com.cdm.ai.entity;

import com.cdm.common.domain.BaseEntity;
import com.cdm.ai.vo.KnowledgeBaseVo;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "knowledge_bases")
@Getter
@Setter
@NoArgsConstructor
public class KnowledgeBaseEntity extends BaseEntity {

    @Column(name = "tenant_id", nullable = false)
    private String tenantId;

    @Column(name = "org_id", nullable = false)
    private String orgId;

    @Column(name = "created_by", nullable = false)
    private String createdBy;

    @Column(nullable = false)
    private String name;

    private String description;

    public static KnowledgeBaseVo toVo(KnowledgeBaseEntity entity) {
        if (entity == null) return null;
        return KnowledgeBaseVo.builder()
                .id(entity.getId())
                .tenantId(entity.getTenantId())
                .orgId(entity.getOrgId())
                .createdBy(entity.getCreatedBy())
                .name(entity.getName())
                .description(entity.getDescription())
                .createdAt(entity.getCreatedAt())
                .build();
    }
}
