package com.cdm.auth.service;

import cn.dev33.satoken.stp.SaLoginConfig;
import cn.dev33.satoken.stp.StpUtil;
import cn.dev33.satoken.temp.SaTempUtil;
import com.cdm.auth.dto.UserReadDto;
import com.cdm.auth.entity.*;
import com.cdm.auth.exception.BusinessException;
import com.cdm.auth.repository.*;
import com.cdm.auth.util.SnowflakeIdGenerator;
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
    public Map<String, Object> register(String email, String password, String name) {
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

        return Map.of("id", user.getId(), "email", email,
                       "tenant_id", tenant.getId(), "org_id", org.getId());
    }

    public Map<String, Object> login(String username, String password) {
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
            return Map.<String, Object>of("id", org.getId(), "name", org.getName(),
                                          "tenant_id", org.getTenantId());
        }).toList();

        var result = new HashMap<String, Object>();
        result.put("access_token", null);
        result.put("token_type", "bearer");
        result.put("organizations", orgList);
        result.put("require_org_selection", true);
        result.put("selection_token", selectionToken);
        return result;
    }

    public Map<String, Object> selectOrg(Long orgId, String selectionToken) {
        Object value = SaTempUtil.parseToken(selectionToken);
        if (value == null || !String.valueOf(value).startsWith("select:")) {
            throw BusinessException.validation("Invalid or expired selection token");
        }
        SaTempUtil.deleteToken(selectionToken);
        Long userId = Long.parseLong(String.valueOf(value).substring("select:".length()));
        var ou = orgUserRepo.findByOrgIdAndUserId(orgId, userId)
                .orElseThrow(() -> BusinessException.forbidden("User is not a member of this organization"));
        var user = userRepo.findById(userId).orElseThrow();
        return loginToOrg(user, ou);
    }

    public Map<String, Object> switchOrg(Long userId, Long orgId) {
        StpUtil.logout();
        var ou = orgUserRepo.findByOrgIdAndUserId(orgId, userId)
                .orElseThrow(() -> BusinessException.forbidden("User is not a member of this organization"));
        var user = userRepo.findById(userId).orElseThrow();
        return loginToOrg(user, ou);
    }

    public List<Map<String, Object>> listMyOrgs(Long userId) {
        return orgUserRepo.findByUserId(userId).stream().map(ou -> {
            var org = orgRepo.findById(ou.getOrgId()).orElseThrow();
            return Map.<String, Object>of("id", org.getId(), "name", org.getName(),
                                          "tenant_id", org.getTenantId());
        }).toList();
    }

    public UserReadDto getMe(Long userId, Long orgId, Long tenantId) {
        var user = userRepo.findById(userId).orElseThrow();
        Set<String> perms = getEffectivePermissions(orgId, userId);
        return UserReadDto.builder()
                .id(user.getId()).email(user.getEmail()).name(user.getName())
                .createdAt(user.getCreatedAt()).tenantId(tenantId).orgId(orgId)
                .permissions(new ArrayList<>(perms)).build();
    }

    public List<Map<String, Object>> getMenuTree(Long userId, Long orgId, Long tenantId) {
        Set<String> permCodes = getEffectivePermissions(orgId, userId);
        return menuService.getMenuTree(tenantId, permCodes);
    }

    // ── 私有方法 ──

    private Map<String, Object> loginToOrg(UserEntity user, OrganizationUserEntity ou) {
        var org = orgRepo.findById(ou.getOrgId()).orElseThrow();
        var roleCodes = getRoleCodes(ou.getOrgId(), ou.getUserId());
        var allowedOrgIds = getDescendingOrgIds(ou.getOrgId());

        StpUtil.login(user.getId(),
                SaLoginConfig
                        .setExtra("tenant_id", org.getTenantId())
                        .setExtra("org_id", org.getId())
                        .setExtra("allowed_org_ids", allowedOrgIds)
                        .setExtra("roles", String.join(",", roleCodes)));

        return Map.of(
                "access_token", StpUtil.getTokenValue(),
                "token_type", "bearer",
                "organization", Map.of("id", org.getId(), "name", org.getName(),
                                       "tenant_id", org.getTenantId()),
                "require_org_selection", false);
    }

    private List<Long> getDescendingOrgIds(Long rootOrgId) {
        List<Long> result = new ArrayList<>();
        Queue<Long> queue = new LinkedList<>();
        queue.add(rootOrgId);
        while (!queue.isEmpty()) {
            Long current = queue.poll();
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

    private List<String> getRoleCodes(Long orgId, Long userId) {
        return orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId).stream()
                .map(our -> roleRepo.findById(our.getRoleId()).map(RoleEntity::getCode).orElse(null))
                .filter(Objects::nonNull).toList();
    }

    private Set<String> getEffectivePermissions(Long orgId, Long userId) {
        var roleIds = orgUserRoleRepo.findByOrgIdAndUserId(orgId, userId).stream()
                .map(OrganizationUserRoleEntity::getRoleId).collect(Collectors.toList());
        Set<Long> allRoleIds = new HashSet<>(roleIds);
        Queue<Long> queue = new LinkedList<>(roleIds);
        while (!queue.isEmpty()) {
            Long rid = queue.poll();
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
