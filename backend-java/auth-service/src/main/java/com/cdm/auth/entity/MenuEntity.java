package com.cdm.auth.entity;

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
    private Long parentId;

    @Column(name = "tenant_id")
    private Long tenantId;

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
}
