package com.cdm.auth.service;

import cn.dev33.satoken.stp.StpUtil;
import com.cdm.auth.dto.LoginRequest;
import com.cdm.auth.dto.LoginResponse;
import com.cdm.auth.entity.User;
import com.cdm.auth.repository.UserRepository;
import com.cdm.auth.util.BCryptUtil;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

@Service
public class AuthService {

    @Autowired
    private UserRepository userRepository;

    public LoginResponse login(LoginRequest request) {
        User user = userRepository.findByEmail(request.getEmail())
            .orElseThrow(() -> new RuntimeException("邮箱或密码错误"));

        if (!BCryptUtil.checkpw(request.getPassword(), user.getHashed_password())) {
            throw new RuntimeException("邮箱或密码错误");
        }

        if (!user.getIs_active()) {
            throw new RuntimeException("该账号已被禁用");
        }

        // --- Sa-Token 登录与附加信息 ---
        StpUtil.login(user.getId());

        // 为了演示微服务透传，我们模拟注入租户和角色信息
        StpUtil.getSession().set("tenant_id", 1L);
        StpUtil.getSession().set("org_id", 100L);
        StpUtil.getSession().set("roles", "admin,user");

        String tokenVal = StpUtil.getTokenValue();
        return new LoginResponse(tokenVal, user.getId(), user.getEmail());
    }
}
