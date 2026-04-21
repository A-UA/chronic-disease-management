package com.cdm.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class SelectOrgRequest {
    @NotNull
    private Long orgId;
    @NotBlank
    private String selectionToken;
}
