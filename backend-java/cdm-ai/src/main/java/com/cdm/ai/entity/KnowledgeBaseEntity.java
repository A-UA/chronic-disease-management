package com.cdm.ai.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.cdm.common.domain.BaseEntity;
import com.cdm.ai.vo.KnowledgeBaseVo;
import lombok.Getter;
import lombok.Setter;
import lombok.NoArgsConstructor;

@TableName("knowledge_bases")
@Getter
@Setter
@NoArgsConstructor
public class KnowledgeBaseEntity extends BaseEntity {

    private Long tenantId;
    private Long orgId;
    private Long createdBy;
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
