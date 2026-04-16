package com.cdm.auth.controller;

import com.cdm.auth.dto.*;
import com.cdm.auth.security.IdentityContext;
import com.cdm.auth.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/register")
    public Map<String, Object> register(@Valid @RequestBody RegisterRequest req) {
        return authService.register(req.getEmail(), req.getPassword(), req.getName());
    }

    @PostMapping("/login/access-token")
    public Map<String, Object> login(@Valid @RequestBody LoginRequest req) {
        return authService.login(req.getUsername(), req.getPassword());
    }

    @PostMapping("/select-org")
    public Map<String, Object> selectOrg(@Valid @RequestBody SelectOrgRequest req) {
        return authService.selectOrg(req.getOrgId(), req.getSelectionToken());
    }

    @PostMapping("/switch-org")
    public Map<String, Object> switchOrg(@Valid @RequestBody SwitchOrgRequest req,
                                         HttpServletRequest httpReq) {
        var ctx = new IdentityContext(httpReq);
        return authService.switchOrg(ctx.getUserId(), req.getOrgId());
    }

    @GetMapping("/my-orgs")
    public List<Map<String, Object>> myOrgs(HttpServletRequest httpReq) {
        var ctx = new IdentityContext(httpReq);
        return authService.listMyOrgs(ctx.getUserId());
    }

    @GetMapping("/me")
    public UserReadDto me(HttpServletRequest httpReq) {
        var ctx = new IdentityContext(httpReq);
        return authService.getMe(ctx.getUserId(), ctx.getOrgId(), ctx.getTenantId());
    }

    @GetMapping("/menu-tree")
    public List<Map<String, Object>> menuTree(HttpServletRequest httpReq) {
        var ctx = new IdentityContext(httpReq);
        return authService.getMenuTree(ctx.getUserId(), ctx.getOrgId(), ctx.getTenantId());
    }
}
