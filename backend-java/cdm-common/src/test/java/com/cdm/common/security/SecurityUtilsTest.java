package com.cdm.common.security;

import com.cdm.common.exception.BusinessException;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertIterableEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class SecurityUtilsTest {

    @AfterEach
    void tearDown() {
        SecurityContextHolder.remove();
    }

    @Test
    void getUserIdThrowsWhenMissing() {
        assertThrows(BusinessException.class, SecurityUtils::getUserId);
    }

    @Test
    void getRolesAndAllowedOrgIdsSplitCommaSeparatedValues() {
        SecurityContextHolder.set(SecurityUtils.USER_ID, "u-1");
        SecurityContextHolder.set(SecurityUtils.ROLES, "doctor,admin");
        SecurityContextHolder.set(SecurityUtils.ALLOWED_ORG_IDS, "org-1,org-2");

        assertEquals("u-1", SecurityUtils.getUserId());
        assertIterableEquals(List.of("doctor", "admin"), SecurityUtils.getRoles());
        assertIterableEquals(List.of("org-1", "org-2"), SecurityUtils.getAllowedOrgIds());
    }
}
