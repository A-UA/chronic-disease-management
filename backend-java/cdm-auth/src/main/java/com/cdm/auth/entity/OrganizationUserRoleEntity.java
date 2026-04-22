package com.cdm.auth.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@TableName("organization_user_roles")
@Getter @Setter @NoArgsConstructor
public class OrganizationUserRoleEntity {

    private Long orgId;
    private Long userId;
    private Long roleId;
    private Long tenantId;
}
