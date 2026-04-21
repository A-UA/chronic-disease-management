package com.cdm.common.security;

import com.cdm.common.exception.BusinessException;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public final class SecurityUtils {
    public static final String USER_ID = "userId";
    public static final String TENANT_ID = "tenantId";
    public static final String ORG_ID = "orgId";
    public static final String ROLES = "roles";
    public static final String ALLOWED_ORG_IDS = "allowedOrgIds";

    private SecurityUtils() {
    }

    public static String getUserId() {
        String userId = SecurityContextHolder.getString(USER_ID);
        if (userId == null || userId.isBlank()) {
            throw BusinessException.unauthorized("无法获取用户身份");
        }
        return userId;
    }

    public static String getTenantId() {
        return SecurityContextHolder.getString(TENANT_ID);
    }

    public static String getOrgId() {
        return SecurityContextHolder.getString(ORG_ID);
    }

    public static List<String> getRoles() {
        String roles = SecurityContextHolder.getString(ROLES);
        if (roles == null || roles.isBlank()) {
            return Collections.emptyList();
        }
        return Arrays.asList(roles.split(","));
    }

    public static List<String> getAllowedOrgIds() {
        String ids = SecurityContextHolder.getString(ALLOWED_ORG_IDS);
        if (ids == null || ids.isBlank()) {
            return Collections.emptyList();
        }
        return Arrays.asList(ids.split(","));
    }
}
