package com.cdm.auth.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.cdm.auth.entity.MenuEntity;
import com.cdm.auth.mapper.MenuMapper;
import com.cdm.auth.vo.MenuVo;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
@RequiredArgsConstructor
public class MenuService {

    private final MenuMapper menuMapper;

    public List<MenuVo> getMenuTree(Long tenantId, Set<String> permCodes) {
        var allMenus = menuMapper.selectList(new LambdaQueryWrapper<MenuEntity>()
                .eq(MenuEntity::getTenantId, tenantId)
                .eq(MenuEntity::getIsVisible, true)
                .orderByAsc(MenuEntity::getSort));
        var visibleMenus = allMenus.stream()
                .filter(m -> m.getPermissionCode() == null
                        || m.getPermissionCode().isEmpty()
                        || permCodes.contains(m.getPermissionCode()))
                .toList();
        return buildTree(visibleMenus);
    }

    private List<MenuVo> buildTree(List<MenuEntity> menus) {
        var menuMap = new LinkedHashMap<Long, MenuVo>();
        for (var m : menus) {
            menuMap.put(m.getId(), MenuEntity.toVo(m));
        }

        var visibleIds = menuMap.keySet();
        var roots = new ArrayList<MenuVo>();
        for (var m : menus) {
            var node = menuMap.get(m.getId());
            if (m.getParentId() != null && visibleIds.contains(m.getParentId())) {
                var parent = menuMap.get(m.getParentId());
                if (parent.getChildren() == null) {
                    parent.setChildren(new ArrayList<>());
                }
                parent.getChildren().add(node);
            } else {
                roots.add(node);
            }
        }
        roots.removeIf(item -> "directory".equals(item.getMenuType())
                && (item.getChildren() == null || item.getChildren().isEmpty()));
        return roots;
    }
}
