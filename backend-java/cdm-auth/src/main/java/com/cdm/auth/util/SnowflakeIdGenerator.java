package com.cdm.auth.util;

import org.springframework.stereotype.Component;

@Component
public class SnowflakeIdGenerator {

    public Long nextId() {
        return Long.valueOf(com.cdm.common.util.SnowflakeIdGenerator.generateId());
    }
}
