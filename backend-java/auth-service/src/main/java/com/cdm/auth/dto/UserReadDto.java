package com.cdm.auth.dto;

import lombok.Builder;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;

@Data @Builder
public class UserReadDto {
    private Long id;
    private String email;
    private String name;
    private LocalDateTime createdAt;
    private Long tenantId;
    private Long orgId;
    private List<String> permissions;
}
