package com.cdm.auth.vo;

import lombok.Data;
import lombok.Builder;
import lombok.AllArgsConstructor;
import lombok.NoArgsConstructor;
import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UserVo {
    private Long id;
    private String email;
    private String name;
    private String tenantId;
    private String orgId;
    private List<String> permissions;
    private LocalDateTime createdAt;
}
