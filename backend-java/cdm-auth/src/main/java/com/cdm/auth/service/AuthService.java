package com.cdm.auth.service;

import cn.dev33.satoken.stp.SaLoginConfig;
import cn.dev33.satoken.stp.StpUtil;
import cn.dev33.satoken.temp.SaTempUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.cdm.auth.vo.*;
import com.cdm.auth.entity.*;
import com.cdm.common.exception.BusinessException;
import com.cdm.common.security.SecurityUtils;
import com.cdm.auth.mapper.*;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserMapper userMapper;
    private final OrganizationMapper orgMapper;
    private final OrganizationUserMapper orgUserMapper;
    private final OrganizationUserRoleMapper orgUserRoleMapper;
    private final RoleMapper roleMapper;
    private final PermissionMapper permMapper;
    private final TenantMapper tenantMapper;
    private final MenuService menuService;

    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    @Transactional
    public LoginVo register(String email, String password, String name) {
        if (userMapper.exists(new LambdaQueryWrapper<UserEntity>().eq(UserEntity::getEmail, email))) {
            throw BusinessException.validation("The user with this email already exists.");
        }

        var user = new UserEntity();
        user.setEmail(email);
        user.setPasswordHash(passwordEncoder.encode(password));
        user.setName(name);
        userMapper.insert(user);

        var tenant = new TenantEntity();
        tenant.setName((name != null ? name : email) + "'s Workspace");
        tenant.setSlug("ws-" + user.getId());
        tenantMapper.insert(tenant);

        var org = new OrganizationEntity();
        org.setTenantId(tenant.getId());
        org.setName("默认部门");
        org.setCode("DEFAULT");
        orgMapper.insert(org);

        var orgUser = new OrganizationUserEntity();
        orgUser.setOrgId(org.getId());
        orgUser.setUserId(user.getId());
        orgUser.setTenantId(tenant.getId());
        orgUserMapper.insert(orgUser);

        RoleEntity ownerRole = roleMapper.selectOne(new LambdaQueryWrapper<RoleEntity>()
                .eq(RoleEntity::getCode, "owner")
                .isNull(RoleEntity::getTenantId));
        if (ownerRole != null) {
            var our = new OrganizationUserRoleEntity();
            our.setOrgId(org.getId());
            our.setUserId(user.getId());
            our.setRoleId(ownerRole.getId());
            our.setTenantId(tenant.getId());
            orgUserRoleMapper.insert(our);
        }
        
        return loginToOrg(user, orgUser);
    }

    public LoginVo login(String username, String password) {
        var user = userMapper.selectOne(new LambdaQueryWrapper<UserEntity>().eq(UserEntity::getEmail, username));
        if (user == null) {
            throw BusinessException.validation("Incorrect email or password");
        }
        if (!verifyPassword(password, user.getPasswordHash())) {
            throw BusinessException.validation("Incorrect email or password");
        }

        var orgUsers = orgUserMapper.selectList(new LambdaQueryWrapper<OrganizationUserEntity>().eq(OrganizationUserEntity::getUserId, user.getId()));
        if (orgUsers.isEmpty()) {
            throw BusinessException.validation("User is not a member of any active organization");
        }

        if (orgUsers.size() == 1) {
            return loginToOrg(user, orgUsers.get(0));
        }

        String selectionToken = SaTempUtil.createToken("select:" + user.getId(), 300);
        var orgList = orgUsers.stream().map(ou -> {
            var org = orgMapper.selectById(ou.getOrgId());
            return OrganizationEntity.toVo(org);
        }).toList();

        return LoginVo.builder()
                .token(selectionToken)
                .organizations(orgList)
                .user(UserEntity.toVo(user))
                .build();
    }

    public LoginVo selectOrg(Long orgId, String selectionToken) {
        Object value = SaTempUtil.parseToken(selectionToken);
        if (value == null || !String.valueOf(value).startsWith("select:")) {
            throw BusinessException.validation("Invalid or expired selection token");
        }
        SaTempUtil.deleteToken(selectionToken);
        Long userId = Long.parseLong(String.valueOf(value).substring("select:".length()));
        var ou = orgUserMapper.selectOne(new LambdaQueryWrapper<OrganizationUserEntity>()
                .eq(OrganizationUserEntity::getOrgId, orgId)
                .eq(OrganizationUserEntity::getUserId, userId));
        if (ou == null) {
            throw BusinessException.forbidden("User is not a member of this organization");
        }
        var user = userMapper.selectById(userId);
        return loginToOrg(user, ou);
    }

    public LoginVo switchOrg(Long orgId) {
        Long userId = Long.parseLong(SecurityUtils.getUserId());
        StpUtil.logout();
        var ou = orgUserMapper.selectOne(new LambdaQueryWrapper<OrganizationUserEntity>()
                .eq(OrganizationUserEntity::getOrgId, orgId)
                .eq(OrganizationUserEntity::getUserId, userId));
        if (ou == null) {
            throw BusinessException.forbidden("User is not a member of this organization");
        }
        var user = userMapper.selectById(userId);
        return loginToOrg(user, ou);
    }

    public List<OrganizationVo> listMyOrgs() {
        Long userId = Long.parseLong(SecurityUtils.getUserId());
        return orgUserMapper.selectList(new LambdaQueryWrapper<OrganizationUserEntity>().eq(OrganizationUserEntity::getUserId, userId))
                .stream().map(ou -> {
            var org = orgMapper.selectById(ou.getOrgId());
            return OrganizationEntity.toVo(org);
        }).toList();
    }

    public UserVo getMe() {
        Long userId = Long.parseLong(SecurityUtils.getUserId());
        Long orgId = Long.parseLong(SecurityUtils.getOrgId());
        String tenantId = SecurityUtils.getTenantId();
        
        var user = userMapper.selectById(userId);
        Set<String> perms = getEffectivePermissions(orgId, userId);
        
        UserVo vo = UserEntity.toVo(user);
        vo.setTenantId(tenantId);
        vo.setOrgId(String.valueOf(orgId));
        vo.setPermissions(new ArrayList<>(perms));
        vo.setCreatedAt(user.getCreatedAt());
        return vo;
    }

    public List<MenuVo> getMenuTree() {
        Long userId = Long.parseLong(SecurityUtils.getUserId());
        Long orgId = Long.parseLong(SecurityUtils.getOrgId());
        Long tenantId = Long.parseLong(SecurityUtils.getTenantId());
        Set<String> permCodes = getEffectivePermissions(orgId, userId);
        return menuService.getMenuTree(tenantId, permCodes);
    }

    // ── 私有方法 ──

    private LoginVo loginToOrg(UserEntity user, OrganizationUserEntity ou) {
        var org = orgMapper.selectById(ou.getOrgId());
        var roleCodes = getRoleCodes(ou.getOrgId(), ou.getUserId());
        var allowedOrgIds = getDescendingOrgIds(ou.getOrgId());

        StpUtil.login(user.getId(),
                SaLoginConfig
                        .setExtra("tenant_id", String.valueOf(org.getTenantId()))
                        .setExtra("org_id", String.valueOf(org.getId()))
                        .setExtra("allowed_org_ids", allowedOrgIds.stream().map(String::valueOf).collect(Collectors.joining(",")))
                        .setExtra("roles", String.join(",", roleCodes)));

        return LoginVo.builder()
                .token(StpUtil.getTokenValue())
                .user(UserEntity.toVo(user))
                .organizations(List.of(OrganizationEntity.toVo(org)))
                .build();
    }

    private List<Long> getDescendingOrgIds(Long rootOrgId) {
        return orgMapper.selectDescendantIds(rootOrgId);
    }

    private boolean verifyPassword(String raw, String hash) {
        if (hash == null) return false;
        if (hash.startsWith("$argon2")) return false;
        return passwordEncoder.matches(raw, hash);
    }

    private List<String> getRoleCodes(Long orgId, Long userId) {
        return roleMapper.selectRoleCodesByOrgAndUser(orgId, userId);
    }

    private Set<String> getEffectivePermissions(Long orgId, Long userId) {
        List<Long> allRoleIds = roleMapper.selectAllRoleIdsByOrgAndUser(orgId, userId);
        if (allRoleIds.isEmpty()) return Set.of();
        return new HashSet<>(permMapper.selectPermCodesByRoleIds(allRoleIds));
    }
}
