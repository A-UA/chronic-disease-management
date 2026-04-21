package com.cdm.auth.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class RegisterDto {
    @Email
    @NotBlank
    private String username;

    @NotBlank
    private String password;

    @NotBlank
    private String tenantName;
}
