package com.cdm.common.util;

import cn.hutool.core.lang.Snowflake;
import cn.hutool.core.util.IdUtil;
import org.springframework.stereotype.Component;

@Component
public class SnowflakeIdGenerator {
    private static final Snowflake SNOWFLAKE = IdUtil.getSnowflake(1, 1);

    public String nextId() {
        return String.valueOf(SNOWFLAKE.nextId());
    }

    public static String generateId() {
        return String.valueOf(SNOWFLAKE.nextId());
    }
}
