package com.cdm.auth.controller;

import com.cdm.auth.dto.*;
import com.cdm.auth.vo.*;
import com.cdm.auth.service.AuthService;
import com.cdm.common.domain.Result;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
@Tag(name = "Authentication", description = "认证与授权接口")
public class AuthController {

    private final AuthService authService;

    @Operation(summary = "用户注册", description = "使用邮箱注册新用户及初始化租户空间")
    @PostMapping("/register")
    public Result<LoginVo> register(@Valid @RequestBody RegisterDto req) {
        return Result.ok(authService.register(req.getUsername(), req.getPassword(), req.getTenantName()));
    }

    @Operation(summary = "用户登录", description = "通过账号密码进行登录获取通行令牌")
    @PostMapping("/login/access-token")
    public Result<LoginVo> login(@Valid @RequestBody LoginDto req) {
        return Result.ok(authService.login(req.getUsername(), req.getPassword()));
    }

    @Operation(summary = "选择组织登录", description = "存在多个组织时选择特定组织换取正式 Token")
    @PostMapping("/select-org")
    public Result<LoginVo> selectOrg(@Valid @RequestBody SelectOrgDto req, @RequestHeader(value = "X-Selection-Token", required = false) String selectionToken) {
        return Result.ok(authService.selectOrg(req.getOrgId(), selectionToken));
    }

    @Operation(summary = "切换组织", description = "在已登录状态下切换当前活动组织")
    @PostMapping("/switch-org")
    public Result<LoginVo> switchOrg(@Valid @RequestBody SelectOrgDto req) {
        return Result.ok(authService.switchOrg(req.getOrgId()));
    }

    @Operation(summary = "当前用户的组织列表", description = "列出用户所挂靠的所有组织")
    @GetMapping("/my-orgs")
    public Result<List<OrganizationVo>> myOrgs() {
        return Result.ok(authService.listMyOrgs());
    }

    @Operation(summary = "当前用户信息", description = "获取当前已身份验证用户的详细信息及权限")
    @GetMapping("/me")
    public Result<UserVo> me() {
        return Result.ok(authService.getMe());
    }

    @Operation(summary = "我的菜单树", description = "根据权限动态推导树形导航栏数据")
    @GetMapping("/menu-tree")
    public Result<List<MenuVo>> menuTree() {
        return Result.ok(authService.getMenuTree());
    }
}
