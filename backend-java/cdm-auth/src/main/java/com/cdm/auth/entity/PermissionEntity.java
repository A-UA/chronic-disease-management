package com.cdm.auth.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@TableName("permissions")
@Getter @Setter @NoArgsConstructor
public class PermissionEntity {

    @TableId(type = IdType.ASSIGN_ID)
    private Long id;

    private String name;
    private String code;
    private Long resourceId;
    private Long actionId;
}
