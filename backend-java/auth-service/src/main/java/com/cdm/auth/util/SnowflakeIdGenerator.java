package com.cdm.auth.util;

import org.springframework.stereotype.Component;

/**
 * 已迁移至 common-lib: com.cdm.common.util.SnowflakeIdGenerator
 * 此类保留为 Spring Bean 适配器，避免 AuthService 大量修改
 */
@Component
public class SnowflakeIdGenerator {

    public long nextId() {
        return com.cdm.common.util.SnowflakeIdGenerator.nextId();
    }
}
