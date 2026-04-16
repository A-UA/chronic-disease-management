package com.cdm.auth.controller;

import cn.dev33.satoken.stp.StpUtil;
import cn.dev33.satoken.annotation.SaCheckLogin;
import com.cdm.auth.dto.LoginRequest;
import com.cdm.auth.dto.LoginResponse;
import com.cdm.auth.service.AuthService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {

    @Autowired
    private AuthService authService;

    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@Validated @RequestBody LoginRequest request) {
        LoginResponse response = authService.login(request);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/logout")
    @SaCheckLogin
    public ResponseEntity<Map<String, String>> logout() {
        StpUtil.logout();
        Map<String, String> result = new HashMap<>();
        result.put("message", "成功登出");
        return ResponseEntity.ok(result);
    }

    @GetMapping("/me")
    @SaCheckLogin
    public ResponseEntity<Map<String, Object>> me() {
        Map<String, Object> result = new HashMap<>();
        result.put("userId", StpUtil.getLoginIdAsLong());
        result.put("tenantId", StpUtil.getSession().get("tenant_id"));
        result.put("orgId", StpUtil.getSession().get("org_id"));
        result.put("roles", StpUtil.getSession().get("roles"));
        return ResponseEntity.ok(result);
    }
}
