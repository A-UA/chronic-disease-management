package com.cdm.gateway.config;

import cn.dev33.satoken.jwt.StpLogicJwtForStateless;
import cn.dev33.satoken.reactor.filter.SaReactorFilter;
import cn.dev33.satoken.router.SaRouter;
import cn.dev33.satoken.stp.StpLogic;
import cn.dev33.satoken.stp.StpUtil;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

@Configuration
public class SaTokenConfig {

    @Bean
    @Primary
    public StpLogic getStpLogicJwt() {
        return new StpLogicJwtForStateless();
    }

    @Bean
    public SaReactorFilter getSaReactorFilter() {
        return new SaReactorFilter()
                .addInclude("/**")
                .addExclude(
                        "/api/v1/auth/login/access-token",
                        "/api/v1/auth/register",
                        "/api/v1/auth/select-org",
                        "/api/v1/auth/forgot-password",
                        "/api/v1/auth/reset-password"
                )
                .setAuth(obj -> {
                    SaRouter.match("/**", r -> StpUtil.checkLogin());
                });
    }

    @Bean
    public GlobalFilter identityHeaderFilter() {
        return (ServerWebExchange exchange, GatewayFilterChain chain) -> {
            if (!StpUtil.isLogin()) {
                return chain.filter(exchange);
            }

            String userId = String.valueOf(StpUtil.getLoginId());
            Object tenantId = StpUtil.getExtra("tenant_id");
            Object orgId = StpUtil.getExtra("org_id");
            Object roles = StpUtil.getExtra("roles");

            ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                    .header("X-User-Id", userId)
                    .header("X-Tenant-Id", tenantId != null ? String.valueOf(tenantId) : "")
                    .header("X-Org-Id", orgId != null ? String.valueOf(orgId) : "")
                    .header("X-Roles", roles != null ? String.valueOf(roles) : "")
                    .build();

            return chain.filter(exchange.mutate().request(mutatedRequest).build());
        };
    }
}
