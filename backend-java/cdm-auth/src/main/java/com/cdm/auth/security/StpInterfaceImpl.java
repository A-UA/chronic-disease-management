package com.cdm.auth.security;

import cn.dev33.satoken.stp.StpInterface;
import cn.dev33.satoken.stp.StpUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.cdm.auth.entity.OrganizationUserRoleEntity;
import com.cdm.auth.entity.PermissionEntity;
import com.cdm.auth.entity.RoleEntity;
import com.cdm.auth.mapper.OrganizationUserRoleMapper;
import com.cdm.auth.mapper.PermissionMapper;
import com.cdm.auth.mapper.RoleMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

@Component
@RequiredArgsConstructor
public class StpInterfaceImpl implements StpInterface {

    private final OrganizationUserRoleMapper orgUserRoleMapper;
    private final RoleMapper roleMapper;
    private final PermissionMapper permMapper;

    @Override
    public List<String> getPermissionList(Object loginId, String loginType) {
        Object orgIdObj = StpUtil.getExtra("org_id");
        if (orgIdObj == null) return List.of();
        Long userId = Long.parseLong(String.valueOf(loginId));
        Long orgId = Long.parseLong(String.valueOf(orgIdObj));

        var roleIds = orgUserRoleMapper.selectList(new LambdaQueryWrapper<OrganizationUserRoleEntity>()
                .eq(OrganizationUserRoleEntity::getOrgId, orgId)
                .eq(OrganizationUserRoleEntity::getUserId, userId))
                .stream().map(OrganizationUserRoleEntity::getRoleId).collect(Collectors.toList());
        Set<Long> allRoleIds = expandRoleHierarchy(roleIds);
        if (allRoleIds.isEmpty()) return List.of();

        return permMapper.selectList(new LambdaQueryWrapper<PermissionEntity>()
                .inSql(PermissionEntity::getId, "SELECT permission_id FROM role_permissions WHERE role_id IN (" +
                        allRoleIds.stream().map(String::valueOf).collect(Collectors.joining(",")) + ")"))
                .stream().map(PermissionEntity::getCode).collect(Collectors.toList());
    }

    @Override
    public List<String> getRoleList(Object loginId, String loginType) {
        Object orgIdObj = StpUtil.getExtra("org_id");
        if (orgIdObj == null) return List.of();
        Long userId = Long.parseLong(String.valueOf(loginId));
        Long orgId = Long.parseLong(String.valueOf(orgIdObj));

        return orgUserRoleMapper.selectList(new LambdaQueryWrapper<OrganizationUserRoleEntity>()
                .eq(OrganizationUserRoleEntity::getOrgId, orgId)
                .eq(OrganizationUserRoleEntity::getUserId, userId)).stream()
                .map(our -> {
                    RoleEntity role = roleMapper.selectById(our.getRoleId());
                    return role != null ? role.getCode() : null;
                })
                .filter(Objects::nonNull).collect(Collectors.toList());
    }

    private Set<Long> expandRoleHierarchy(List<Long> roleIds) {
        Set<Long> all = new HashSet<>(roleIds);
        Queue<Long> queue = new LinkedList<>(roleIds);
        while (!queue.isEmpty()) {
            Long rid = queue.poll();
            RoleEntity role = roleMapper.selectById(rid);
            if (role != null) {
                if (role.getParentRoleId() != null && all.add(role.getParentRoleId())) {
                    queue.add(role.getParentRoleId());
                }
            }
        }
        return all;
    }
}
