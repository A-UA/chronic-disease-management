package com.cdm.auth.service;

import com.cdm.auth.entity.MenuEntity;
import com.cdm.auth.repository.MenuRepository;
import com.cdm.auth.vo.MenuVo;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
@RequiredArgsConstructor
public class MenuService {

    private final MenuRepository menuRepo;

    public List<MenuVo> getMenuTree(String tenantId, Set<String> permCodes) {
        var allMenus = menuRepo.findActiveMenus(tenantId);
        var visibleMenus = allMenus.stream()
                .filter(m -> m.getPermissionCode() == null
                        || m.getPermissionCode().isEmpty()
                        || permCodes.contains(m.getPermissionCode()))
                .toList();
        return buildTree(visibleMenus);
    }

    private List<MenuVo> buildTree(List<MenuEntity> menus) {
        var menuMap = new LinkedHashMap<String, MenuVo>();
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
