package com.cdm.auth.service;

import com.cdm.auth.entity.MenuEntity;
import com.cdm.auth.repository.MenuRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
@RequiredArgsConstructor
public class MenuService {

    private final MenuRepository menuRepo;

    public List<Map<String, Object>> getMenuTree(Long tenantId, Set<String> permCodes) {
        var allMenus = menuRepo.findActiveMenus(tenantId);
        var visibleMenus = allMenus.stream()
                .filter(m -> m.getPermissionCode() == null
                        || m.getPermissionCode().isEmpty()
                        || permCodes.contains(m.getPermissionCode()))
                .toList();
        return buildTree(visibleMenus);
    }

    private List<Map<String, Object>> buildTree(List<MenuEntity> menus) {
        var menuMap = new LinkedHashMap<Long, Map<String, Object>>();
        for (var m : menus) {
            var node = new LinkedHashMap<String, Object>();
            node.put("id", m.getId());
            node.put("name", m.getName());
            node.put("code", m.getCode());
            node.put("menu_type", m.getMenuType());
            node.put("path", m.getPath());
            node.put("icon", m.getIcon());
            node.put("permission_code", m.getPermissionCode());
            node.put("sort", m.getSort());
            node.put("is_visible", m.getIsVisible());
            node.put("is_enabled", m.getIsEnabled());
            node.put("meta", m.getMeta());
            node.put("children", new ArrayList<Map<String, Object>>());
            menuMap.put(m.getId(), node);
        }

        var visibleIds = menuMap.keySet();
        var roots = new ArrayList<Map<String, Object>>();
        for (var m : menus) {
            var node = menuMap.get(m.getId());
            if (m.getParentId() != null && visibleIds.contains(m.getParentId())) {
                @SuppressWarnings("unchecked")
                var children = (List<Map<String, Object>>) menuMap.get(m.getParentId()).get("children");
                children.add(node);
            } else {
                roots.add(node);
            }
        }
        roots.removeIf(item -> "directory".equals(item.get("menu_type"))
                && ((List<?>) item.get("children")).isEmpty());
        return roots;
    }
}
