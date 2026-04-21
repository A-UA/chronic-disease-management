package com.cdm.gateway.config;

import cn.dev33.satoken.jwt.StpLogicJwtForStateless;
import cn.dev33.satoken.stp.StpLogic;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

@Configuration
@EnableConfigurationProperties(IgnoreWhiteProperties.class)
public class SaTokenConfig {

    @Bean
    @Primary
    public StpLogic getStpLogicJwt() {
        return new StpLogicJwtForStateless();
    }
}
