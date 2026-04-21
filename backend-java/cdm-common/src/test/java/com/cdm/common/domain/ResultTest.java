package com.cdm.common.domain;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class ResultTest {

    @Test
    void okUsesSuccessCodeAndPayload() {
        Result<String> result = Result.ok("payload");

        assertEquals(200, result.getCode());
        assertEquals("操作成功", result.getMessage());
        assertEquals("payload", result.getData());
    }

    @Test
    void failUsesProvidedMessage() {
        Result<Void> result = Result.fail(ResultCode.BAD_REQUEST, "bad input");

        assertEquals(400, result.getCode());
        assertEquals("bad input", result.getMessage());
        assertNull(result.getData());
    }
}
