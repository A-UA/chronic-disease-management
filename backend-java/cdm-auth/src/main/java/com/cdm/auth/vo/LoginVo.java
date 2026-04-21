package com.cdm.auth.vo;

import lombok.Data;
import lombok.Builder;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class LoginVo {
    private String token;
    private UserVo user;
    private List<OrganizationVo> organizations;
}
