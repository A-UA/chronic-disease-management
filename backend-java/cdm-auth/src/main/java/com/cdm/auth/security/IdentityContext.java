package com.cdm.auth.security;

import jakarta.servlet.http.HttpServletRequest;
import lombok.Getter;
import java.util.Arrays;
import java.util.List;

@Getter
public class IdentityContext {
    private final Long userId;
    private final Long tenantId;
    private final Long orgId;
    private final List<String> roles;

    public IdentityContext(HttpServletRequest request) {
        this.userId = parseLong(request.getHeader("X-User-Id"));
        this.tenantId = parseLong(request.getHeader("X-Tenant-Id"));
        this.orgId = parseLong(request.getHeader("X-Org-Id"));
        String rolesHeader = request.getHeader("X-Roles");
        this.roles = rolesHeader != null && !rolesHeader.isEmpty()
                ? Arrays.asList(rolesHeader.split(",")) : List.of();
    }

    private Long parseLong(String value) {
        if (value == null || value.isEmpty()) return null;
        try { return Long.parseLong(value); } catch (NumberFormatException e) { return null; }
    }
}
