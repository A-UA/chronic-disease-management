package com.cdm.auth.vo;

import lombok.Data;
import lombok.Builder;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import java.util.Map;
import java.util.List;
import java.util.ArrayList;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MenuVo {
    private Long id;
    private Long parentId;
    private String name;
    private String code;
    private String menuType;
    private String path;
    private String icon;
    private String permissionCode;
    private Integer sort;
    private Boolean isVisible;
    private Boolean isEnabled;
    private Map<String, Object> meta;

    @Builder.Default
    private List<MenuVo> children = new ArrayList<>();
}
