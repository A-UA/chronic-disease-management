package com.cdm.common.feign;

import com.cdm.common.security.SecurityContextHolder;
import com.cdm.common.security.SecurityUtils;
import feign.RequestInterceptor;
import feign.RequestTemplate;

public class FeignRequestInterceptor implements RequestInterceptor {
    @Override
    public void apply(RequestTemplate template) {
        addHeader(template, "X-User-Id", SecurityUtils.USER_ID);
        addHeader(template, "X-Tenant-Id", SecurityUtils.TENANT_ID);
        addHeader(template, "X-Org-Id", SecurityUtils.ORG_ID);
        addHeader(template, "X-Roles", SecurityUtils.ROLES);
        addHeader(template, "X-Allowed-Org-Ids", SecurityUtils.ALLOWED_ORG_IDS);
    }

    private void addHeader(RequestTemplate template, String headerName, String contextKey) {
        String value = SecurityContextHolder.getString(contextKey);
        if (value != null && !value.isBlank()) {
            template.header(headerName, value);
        }
    }
}
