package com.cdm.common.util;

import cn.hutool.core.lang.Snowflake;
import cn.hutool.core.util.IdUtil;

/**
 * 基于 Hutool 的统一雪花 ID 生成器
 * workerId=1, datacenterId=1
 * 纪元: Hutool 默认 (2010-11-04)，与 NestJS 端各自独立生成，仅需保证全局唯一
 */
public class SnowflakeIdGenerator {

    private static final Snowflake SNOWFLAKE = IdUtil.getSnowflake(1, 1);

    private SnowflakeIdGenerator() {}

    /**
     * 生成全局唯一雪花 ID
     */
    public static long nextId() {
        return SNOWFLAKE.nextId();
    }
}
