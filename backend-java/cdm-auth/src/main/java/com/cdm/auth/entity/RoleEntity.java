package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "roles")
@Getter @Setter @NoArgsConstructor
public class RoleEntity extends BaseEntity {

    @Column(name = "tenant_id")
    private String tenantId;

    @Column(name = "parent_role_id")
    private String parentRoleId;

    @Column(nullable = false, length = 100)
    private String name;

    @Column(nullable = false, length = 100)
    private String code;

    @Column(name = "is_system")
    private Boolean isSystem = false;

    @ManyToMany
    @JoinTable(name = "role_permissions",
        joinColumns = @JoinColumn(name = "role_id"),
        inverseJoinColumns = @JoinColumn(name = "permission_id"))
    private List<PermissionEntity> permissions = new ArrayList<>();
}
