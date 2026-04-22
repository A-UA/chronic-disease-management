package com.cdm.auth.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.cdm.auth.vo.OrganizationVo;
import com.cdm.common.domain.BaseEntity;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@TableName("organizations")
@Getter @Setter @NoArgsConstructor
public class OrganizationEntity extends BaseEntity {

    private Long tenantId;
    private Long parentId;
    private String name;
    private String code;
    private String status = "active";

    public static OrganizationVo toVo(OrganizationEntity entity) {
        if (entity == null) return null;
        return OrganizationVo.builder()
                .id(entity.getId())
                .tenantId(entity.getTenantId())
                .parentId(entity.getParentId())
                .name(entity.getName())
                .code(entity.getCode())
                .status(entity.getStatus())
                .build();
    }
}
