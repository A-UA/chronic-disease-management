package com.cdm.auth.vo;

import lombok.Data;
import lombok.Builder;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OrganizationVo {
    private Long id;
    private Long tenantId;
    private Long parentId;
    private String name;
    private String code;
    private String status;
}
