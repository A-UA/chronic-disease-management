package com.cdm.auth.security;

import cn.dev33.satoken.stp.StpInterface;
import cn.dev33.satoken.stp.StpUtil;
import com.cdm.auth.mapper.PermissionMapper;
import com.cdm.auth.mapper.RoleMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.*;

@Component
@RequiredArgsConstructor
public class StpInterfaceImpl implements StpInterface {

    private final RoleMapper roleMapper;
    private final PermissionMapper permMapper;

    @Override
    public List<String> getPermissionList(Object loginId, String loginType) {
        Object orgIdObj = StpUtil.getExtra("org_id");
        if (orgIdObj == null) return List.of();
        Long userId = Long.parseLong(String.valueOf(loginId));
        Long orgId = Long.parseLong(String.valueOf(orgIdObj));

        List<Long> allRoleIds = roleMapper.selectAllRoleIdsByOrgAndUser(orgId, userId);
        if (allRoleIds.isEmpty()) return List.of();

        return permMapper.selectPermCodesByRoleIds(allRoleIds);
    }

    @Override
    public List<String> getRoleList(Object loginId, String loginType) {
        Object orgIdObj = StpUtil.getExtra("org_id");
        if (orgIdObj == null) return List.of();
        Long userId = Long.parseLong(String.valueOf(loginId));
        Long orgId = Long.parseLong(String.valueOf(orgIdObj));

        return roleMapper.selectRoleCodesByOrgAndUser(orgId, userId);
    }
}

