package com.cdm.auth.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import com.cdm.common.domain.BaseEntity;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.util.ArrayList;
import java.util.List;

@TableName("roles")
@Getter @Setter @NoArgsConstructor
public class RoleEntity extends BaseEntity {

    private Long tenantId;
    private Long parentRoleId;
    private String name;
    private String code;
    private Boolean isSystem = false;

    @TableField(exist = false)
    private List<PermissionEntity> permissions = new ArrayList<>();
}
