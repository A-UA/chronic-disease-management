package com.cdm.common.security;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.web.servlet.AsyncHandlerInterceptor;

public class HeaderInterceptor implements AsyncHandlerInterceptor {
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        SecurityContextHolder.set(SecurityUtils.USER_ID, request.getHeader("X-User-Id"));
        SecurityContextHolder.set(SecurityUtils.TENANT_ID, request.getHeader("X-Tenant-Id"));
        SecurityContextHolder.set(SecurityUtils.ORG_ID, request.getHeader("X-Org-Id"));
        SecurityContextHolder.set(SecurityUtils.ROLES, request.getHeader("X-Roles"));
        SecurityContextHolder.set(SecurityUtils.ALLOWED_ORG_IDS, request.getHeader("X-Allowed-Org-Ids"));
        return true;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        SecurityContextHolder.remove();
    }
}
