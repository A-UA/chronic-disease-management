package com.cdm.auth.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class SelectOrgDto {
    @NotBlank
    private String orgId;
}
