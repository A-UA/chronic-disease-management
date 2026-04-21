package com.cdm.auth.security;

import cn.dev33.satoken.stp.StpInterface;
import cn.dev33.satoken.stp.StpUtil;
import com.cdm.auth.entity.OrganizationUserRoleEntity;
import com.cdm.auth.entity.RoleEntity;
import com.cdm.auth.repository.OrganizationUserRoleRepository;
import com.cdm.auth.repository.PermissionRepository;
import com.cdm.auth.repository.RoleRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.*;
import java.util.stream.Collectors;

@Component
@RequiredArgsConstructor
public class StpInterfaceImpl implements StpInterface {

    private final OrganizationUserRoleRepository orgUserRoleRepo;
    private final RoleRepository roleRepo;
    private final PermissionRepository permRepo;

    @Override
    public List<String> getPermissionList(Object loginId, String loginType) {
        Object orgIdObj = StpUtil.getExtra("org_id");
        if (orgIdObj == null) return List.of();
        String userId = String.valueOf(loginId);
        String orgId = String.valueOf(orgIdObj);

        var roleIds = orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId)
                .stream().map(OrganizationUserRoleEntity::getRoleId).collect(Collectors.toList());
        Set<String> allRoleIds = expandRoleHierarchy(roleIds);
        if (allRoleIds.isEmpty()) return List.of();

        return new ArrayList<>(permRepo.findCodesByRoleIds(new ArrayList<>(allRoleIds)));
    }

    @Override
    public List<String> getRoleList(Object loginId, String loginType) {
        Object orgIdObj = StpUtil.getExtra("org_id");
        if (orgIdObj == null) return List.of();
        String userId = String.valueOf(loginId);
        String orgId = String.valueOf(orgIdObj);

        return orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId).stream()
                .map(our -> roleRepo.findById(our.getRoleId()).map(RoleEntity::getCode).orElse(null))
                .filter(Objects::nonNull).collect(Collectors.toList());
    }

    private Set<String> expandRoleHierarchy(List<String> roleIds) {
        Set<String> all = new HashSet<>(roleIds);
        Queue<String> queue = new LinkedList<>(roleIds);
        while (!queue.isEmpty()) {
            String rid = queue.poll();
            roleRepo.findById(rid).ifPresent(role -> {
                if (role.getParentRoleId() != null && all.add(role.getParentRoleId())) {
                    queue.add(role.getParentRoleId());
                }
            });
        }
        return all;
    }
}
