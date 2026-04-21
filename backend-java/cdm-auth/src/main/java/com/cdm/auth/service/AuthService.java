package com.cdm.auth.service;

import cn.dev33.satoken.stp.SaLoginConfig;
import cn.dev33.satoken.stp.StpUtil;
import cn.dev33.satoken.temp.SaTempUtil;
import com.cdm.auth.vo.*;
import com.cdm.auth.entity.*;
import com.cdm.common.exception.BusinessException;
import com.cdm.common.security.SecurityUtils;
import com.cdm.auth.repository.*;
import com.cdm.common.util.SnowflakeIdGenerator;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepo;
    private final OrganizationRepository orgRepo;
    private final OrganizationUserRepository orgUserRepo;
    private final OrganizationUserRoleRepository orgUserRoleRepo;
    private final RoleRepository roleRepo;
    private final PermissionRepository permRepo;
    private final MenuService menuService;
    private final SnowflakeIdGenerator idGenerator;

    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    @Transactional
    public LoginVo register(String email, String password, String name) {
        if (userRepo.existsByEmail(email)) {
            throw BusinessException.validation("The user with this email already exists.");
        }

        var user = new UserEntity();
        user.setId(idGenerator.nextId());
        user.setEmail(email);
        user.setPasswordHash(passwordEncoder.encode(password));
        user.setName(name);
        userRepo.save(user);

        var tenant = new TenantEntity();
        tenant.setId(idGenerator.nextId());
        tenant.setName((name != null ? name : email) + "'s Workspace");
        tenant.setSlug("ws-" + user.getId());

        var org = new OrganizationEntity();
        org.setId(idGenerator.nextId());
        org.setTenantId(tenant.getId());
        org.setName("默认部门");
        org.setCode("DEFAULT");

        var orgUser = new OrganizationUserEntity();
        orgUser.setOrgId(org.getId());
        orgUser.setUserId(user.getId());
        orgUser.setTenantId(tenant.getId());

        orgRepo.save(org);
        orgUserRepo.save(orgUser);

        roleRepo.findByCodeAndTenantIdIsNull("owner").ifPresent(ownerRole -> {
            var our = new OrganizationUserRoleEntity();
            our.setOrgId(org.getId());
            our.setUserId(user.getId());
            our.setRoleId(ownerRole.getId());
            our.setTenantId(tenant.getId());
            orgUserRoleRepo.save(our);
        });
        
        return loginToOrg(user, orgUser);
    }

    public LoginVo login(String username, String password) {
        var user = userRepo.findByEmail(username)
                .orElseThrow(() -> BusinessException.validation("Incorrect email or password"));
        if (!verifyPassword(password, user.getPasswordHash())) {
            throw BusinessException.validation("Incorrect email or password");
        }

        var orgUsers = orgUserRepo.findByUserId(user.getId());
        if (orgUsers.isEmpty()) {
            throw BusinessException.validation("User is not a member of any active organization");
        }

        if (orgUsers.size() == 1) {
            return loginToOrg(user, orgUsers.get(0));
        }

        String selectionToken = SaTempUtil.createToken("select:" + user.getId(), 300);
        var orgList = orgUsers.stream().map(ou -> {
            var org = orgRepo.findById(ou.getOrgId()).orElseThrow();
            return OrganizationEntity.toVo(org);
        }).toList();

        return LoginVo.builder()
                .token(selectionToken)
                .organizations(orgList)
                .user(UserEntity.toVo(user))
                .build();
    }

    public LoginVo selectOrg(String orgId, String selectionToken) {
        Object value = SaTempUtil.parseToken(selectionToken);
        if (value == null || !String.valueOf(value).startsWith("select:")) {
            throw BusinessException.validation("Invalid or expired selection token");
        }
        SaTempUtil.deleteToken(selectionToken);
        String userId = String.valueOf(value).substring("select:".length());
        var ou = orgUserRepo.findByOrgIdAndUserId(orgId, userId)
                .orElseThrow(() -> BusinessException.forbidden("User is not a member of this organization"));
        var user = userRepo.findById(userId).orElseThrow();
        return loginToOrg(user, ou);
    }

    public LoginVo switchOrg(String orgId) {
        String userId = SecurityUtils.getUserId();
        StpUtil.logout();
        var ou = orgUserRepo.findByOrgIdAndUserId(orgId, userId)
                .orElseThrow(() -> BusinessException.forbidden("User is not a member of this organization"));
        var user = userRepo.findById(userId).orElseThrow();
        return loginToOrg(user, ou);
    }

    public List<OrganizationVo> listMyOrgs() {
        String userId = SecurityUtils.getUserId();
        return orgUserRepo.findByUserId(userId).stream().map(ou -> {
            var org = orgRepo.findById(ou.getOrgId()).orElseThrow();
            return OrganizationEntity.toVo(org);
        }).toList();
    }

    public UserVo getMe() {
        String userId = SecurityUtils.getUserId();
        String orgId = SecurityUtils.getOrgId();
        String tenantId = SecurityUtils.getTenantId();
        
        var user = userRepo.findById(userId).orElseThrow();
        Set<String> perms = getEffectivePermissions(orgId, userId);
        
        UserVo vo = UserEntity.toVo(user);
        vo.setTenantId(tenantId);
        vo.setOrgId(orgId);
        vo.setPermissions(new ArrayList<>(perms));
        vo.setCreatedAt(user.getCreatedAt());
        return vo;
    }

    public List<MenuVo> getMenuTree() {
        String userId = SecurityUtils.getUserId();
        String orgId = SecurityUtils.getOrgId();
        String tenantId = SecurityUtils.getTenantId();
        Set<String> permCodes = getEffectivePermissions(orgId, userId);
        return menuService.getMenuTree(tenantId, permCodes);
    }

    // ── 私有方法 ──

    private LoginVo loginToOrg(UserEntity user, OrganizationUserEntity ou) {
        var org = orgRepo.findById(ou.getOrgId()).orElseThrow();
        var roleCodes = getRoleCodes(ou.getOrgId(), ou.getUserId());
        var allowedOrgIds = getDescendingOrgIds(ou.getOrgId());

        StpUtil.login(user.getId(),
                SaLoginConfig
                        .setExtra("tenant_id", org.getTenantId())
                        .setExtra("org_id", org.getId())
                        .setExtra("allowed_org_ids", String.join(",", allowedOrgIds))
                        .setExtra("roles", String.join(",", roleCodes)));

        return LoginVo.builder()
                .token(StpUtil.getTokenValue())
                .user(UserEntity.toVo(user))
                .organizations(List.of(OrganizationEntity.toVo(org)))
                .build();
    }

    private List<String> getDescendingOrgIds(String rootOrgId) {
        List<String> result = new ArrayList<>();
        Queue<String> queue = new LinkedList<>();
        queue.add(rootOrgId);
        while (!queue.isEmpty()) {
            String current = queue.poll();
            if (!result.contains(current)) {
                result.add(current);
                List<OrganizationEntity> children = orgRepo.findByParentId(current);
                for (OrganizationEntity child : children) {
                    queue.add(child.getId());
                }
            }
        }
        return result;
    }

    private boolean verifyPassword(String raw, String hash) {
        if (hash == null) return false;
        if (hash.startsWith("$argon2")) return false;
        return passwordEncoder.matches(raw, hash);
    }

    private List<String> getRoleCodes(String orgId, String userId) {
        return orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId).stream()
                .map(our -> roleRepo.findById(our.getRoleId()).map(RoleEntity::getCode).orElse(null))
                .filter(Objects::nonNull).toList();
    }

    private Set<String> getEffectivePermissions(String orgId, String userId) {
        var roleIds = orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId).stream()
                .map(OrganizationUserRoleEntity::getRoleId).collect(Collectors.toList());
        Set<String> allRoleIds = new HashSet<>(roleIds);
        Queue<String> queue = new LinkedList<>(roleIds);
        while (!queue.isEmpty()) {
            String rid = queue.poll();
            roleRepo.findById(rid).ifPresent(role -> {
                if (role.getParentRoleId() != null && allRoleIds.add(role.getParentRoleId())) {
                    queue.add(role.getParentRoleId());
                }
            });
        }
        if (allRoleIds.isEmpty()) return Set.of();
        return permRepo.findCodesByRoleIds(new ArrayList<>(allRoleIds));
    }
}
