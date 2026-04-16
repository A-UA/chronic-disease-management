package com.cdm.gateway.config;

import cn.dev33.satoken.reactor.filter.SaReactorFilter;
import cn.dev33.satoken.router.SaRouter;
import cn.dev33.satoken.stp.StpUtil;
import cn.dev33.satoken.exception.NotLoginException;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.HashMap;
import java.util.Map;

@Configuration
public class SaTokenConfig {

    @Bean
    public SaReactorFilter getSaReactorFilter() {
        return new SaReactorFilter()
            .addInclude("/**")
            .addExclude("/favicon.ico", "/api/v1/auth/login", "/api/v1/auth/register")
            .setAuth(obj -> {
                SaRouter.match("/**", r -> StpUtil.checkLogin());
            })
            .setError(e -> {
                Map<String, Object> map = new HashMap<>();
                if (e instanceof NotLoginException) {
                    map.put("code", 401);
                    map.put("message", "未登录或 token 已过期");
                } else {
                    map.put("code", 500);
                    map.put("message", e.getMessage());
                }
                return map;
            })
            .setBeforeAuth(obj -> {
                if (StpUtil.isLogin()) {
                    long userId = StpUtil.getLoginIdAsLong();
                    Object tenantId = StpUtil.getExtra("tenant_id");
                    Object orgId = StpUtil.getExtra("org_id");
                    Object roles = StpUtil.getExtra("roles");

                    cn.dev33.satoken.context.SaHolder.getRequest()
                        .mutate()
                        .headers(h -> {
                            h.add("X-User-Id", String.valueOf(userId));
                            if (tenantId != null) h.add("X-Tenant-Id", String.valueOf(tenantId));
                            if (orgId != null) h.add("X-Org-Id", String.valueOf(orgId));
                            if (roles != null) h.add("X-Roles", String.valueOf(roles));
                        });
                }
            });
    }
}
