package com.cdm.gateway.filter;

import cn.dev33.satoken.stp.StpUtil;
import com.cdm.gateway.config.IgnoreWhiteProperties;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import reactor.core.publisher.Mono;

import java.util.List;

@Component
public class AuthFilter implements GlobalFilter, Ordered {
    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();
    private static final List<String> FORWARDED_HEADERS = List.of(
            "X-User-Id",
            "X-Tenant-Id",
            "X-Org-Id",
            "X-Roles",
            "X-Allowed-Org-Ids"
    );

    private final IgnoreWhiteProperties ignoreWhiteProperties;

    public AuthFilter(IgnoreWhiteProperties ignoreWhiteProperties) {
        this.ignoreWhiteProperties = ignoreWhiteProperties;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getURI().getPath();
        if (isWhitelisted(path)) {
            return chain.filter(exchange.mutate().request(sanitize(exchange.getRequest())).build());
        }

        if (!StpUtil.isLogin()) {
            ServerHttpResponse response = exchange.getResponse();
            response.setStatusCode(HttpStatus.UNAUTHORIZED);
            return response.setComplete();
        }

        ServerHttpRequest sanitizedRequest = sanitize(exchange.getRequest()).mutate()
                .header("X-User-Id", String.valueOf(StpUtil.getLoginId()))
                .header("X-Tenant-Id", String.valueOf(StpUtil.getExtra("tenant_id")))
                .header("X-Org-Id", String.valueOf(StpUtil.getExtra("org_id")))
                .header("X-Roles", String.valueOf(StpUtil.getExtra("roles")))
                .header("X-Allowed-Org-Ids", String.valueOf(StpUtil.getExtra("allowed_org_ids")))
                .build();

        return chain.filter(exchange.mutate().request(sanitizedRequest).build());
    }

    @Override
    public int getOrder() {
        return -200;
    }

    private boolean isWhitelisted(String path) {
        return ignoreWhiteProperties.getWhites().stream().anyMatch(pattern -> PATH_MATCHER.match(pattern, path));
    }

    private ServerHttpRequest sanitize(ServerHttpRequest request) {
        ServerHttpRequest.Builder builder = request.mutate();
        FORWARDED_HEADERS.forEach(header -> builder.headers(headers -> headers.remove(header)));
        return builder.build();
    }
}
