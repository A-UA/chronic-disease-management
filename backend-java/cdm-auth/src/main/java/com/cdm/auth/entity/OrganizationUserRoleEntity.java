package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.io.Serializable;

@Entity
@Table(name = "organization_user_roles")
@IdClass(OrganizationUserRoleEntity.PK.class)
@Getter @Setter @NoArgsConstructor
public class OrganizationUserRoleEntity {

    @Id @Column(name = "org_id")
    private Long orgId;

    @Id @Column(name = "user_id")
    private Long userId;

    @Id @Column(name = "role_id")
    private Long roleId;

    @Column(name = "tenant_id", nullable = false)
    private Long tenantId;

    @Getter @Setter @NoArgsConstructor
    public static class PK implements Serializable {
        private Long orgId;
        private Long userId;
        private Long roleId;
    }
}
