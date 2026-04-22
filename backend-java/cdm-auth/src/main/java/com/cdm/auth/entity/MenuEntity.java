package com.cdm.auth.entity;

import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableName;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import com.cdm.auth.vo.MenuVo;
import com.cdm.common.domain.BaseEntity;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.util.Map;

@TableName(value = "menus", autoResultMap = true)
@Getter @Setter @NoArgsConstructor
public class MenuEntity extends BaseEntity {

    private Long parentId;
    private Long tenantId;
    private String name;
    private String code;
    private String menuType = "page";
    private String path;
    private String icon;
    private String permissionCode;
    private Integer sort = 0;
    private Boolean isVisible = true;
    private Boolean isEnabled = true;

    @TableField(typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> meta;

    public static MenuVo toVo(MenuEntity entity) {
        if (entity == null) return null;
        return MenuVo.builder()
                .id(entity.getId())
                .parentId(entity.getParentId())
                .name(entity.getName())
                .code(entity.getCode())
                .menuType(entity.getMenuType())
                .path(entity.getPath())
                .icon(entity.getIcon())
                .permissionCode(entity.getPermissionCode())
                .sort(entity.getSort())
                .isVisible(entity.getIsVisible())
                .isEnabled(entity.getIsEnabled())
                .meta(entity.getMeta())
                .build();
    }
}
