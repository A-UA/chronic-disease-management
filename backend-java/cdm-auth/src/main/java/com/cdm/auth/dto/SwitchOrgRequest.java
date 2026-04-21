package com.cdm.auth.dto;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class SwitchOrgRequest {
    @NotNull
    private Long orgId;
}
