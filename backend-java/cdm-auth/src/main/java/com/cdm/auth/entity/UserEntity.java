package com.cdm.auth.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import com.cdm.auth.vo.UserVo;
import com.cdm.common.domain.BaseEntity;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@TableName("users")
@Getter @Setter @NoArgsConstructor
public class UserEntity extends BaseEntity {

    private String email;

    private String passwordHash;

    private String name;

    public static UserVo toVo(UserEntity entity) {
        if (entity == null) return null;
        return UserVo.builder()
                .id(entity.getId())
                .email(entity.getEmail())
                .name(entity.getName())
                .build();
    }
}
