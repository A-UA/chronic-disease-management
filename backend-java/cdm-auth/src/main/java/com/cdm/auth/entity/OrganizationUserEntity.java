package com.cdm.auth.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@TableName("organization_users")
@Getter @Setter @NoArgsConstructor
public class OrganizationUserEntity {

    private Long orgId;
    private Long userId;
    private Long tenantId;
    private String userType = "staff";
}
