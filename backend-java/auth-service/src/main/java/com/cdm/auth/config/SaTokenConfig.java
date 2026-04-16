package com.cdm.auth.config;

import cn.dev33.satoken.jwt.StpLogicJwtForStateless;
import cn.dev33.satoken.stp.StpLogic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;

@Configuration
public class SaTokenConfig {
    @Bean
    @Primary
    public StpLogic getStpLogicJwt() {
        return new StpLogicJwtForStateless();
    }
}
