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
    private String orgId;

    @Id @Column(name = "user_id")
    private String userId;

    @Id @Column(name = "role_id")
    private String roleId;

    @Column(name = "tenant_id", nullable = false)
    private String tenantId;

    @Getter @Setter @NoArgsConstructor
    public static class PK implements Serializable {
        private String orgId;
        private String userId;
        private String roleId;
    }
}
