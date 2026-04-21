package com.cdm.auth.entity;

import com.cdm.auth.vo.MenuVo;
import com.cdm.common.domain.BaseEntity;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import java.util.Map;

@Entity
@Table(name = "menus")
@Getter @Setter @NoArgsConstructor
public class MenuEntity extends BaseEntity {

    @Column(name = "parent_id")
    private String parentId;

    @Column(name = "tenant_id")
    private String tenantId;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, unique = true, length = 100)
    private String code;

    @Column(name = "menu_type", nullable = false, length = 20)
    private String menuType = "page";

    @Column(length = 255)
    private String path;

    @Column(length = 50)
    private String icon;

    @Column(name = "permission_code", length = 100)
    private String permissionCode;

    @Column
    private Integer sort = 0;

    @Column(name = "is_visible")
    private Boolean isVisible = true;

    @Column(name = "is_enabled")
    private Boolean isEnabled = true;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(columnDefinition = "jsonb")
    private Map<String, Object> meta;

    public static MenuVo toVo(MenuEntity entity) {
        if (entity == null) return null;
        return MenuVo.builder()
                .id(entity.getId())
                .parentId(entity.getParentId() != null ? String.valueOf(entity.getParentId()) : null)
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
