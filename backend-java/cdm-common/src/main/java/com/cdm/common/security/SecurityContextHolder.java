package com.cdm.common.security;

import com.alibaba.ttl.TransmittableThreadLocal;

import java.util.HashMap;
import java.util.Map;

public final class SecurityContextHolder {
    private static final TransmittableThreadLocal<Map<String, Object>> CONTEXT =
            new TransmittableThreadLocal<>() {
                @Override
                protected Map<String, Object> initialValue() {
                    return new HashMap<>();
                }
            };

    private SecurityContextHolder() {
    }

    public static void set(String key, Object value) {
        CONTEXT.get().put(key, value);
    }

    public static <T> T get(String key, Class<T> clazz) {
        Object value = CONTEXT.get().get(key);
        if (value == null) {
            return null;
        }
        return clazz.cast(value);
    }

    public static String getString(String key) {
        Object value = CONTEXT.get().get(key);
        return value == null ? null : value.toString();
    }

    public static void remove() {
        CONTEXT.remove();
    }
}
