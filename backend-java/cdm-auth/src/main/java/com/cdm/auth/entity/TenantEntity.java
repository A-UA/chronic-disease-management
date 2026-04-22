package com.cdm.auth.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.cdm.common.domain.BaseEntity;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@TableName("tenants")
@Getter @Setter @NoArgsConstructor
public class TenantEntity extends BaseEntity {

    private String name;
    private String slug;
    private String planType = "free";
}
