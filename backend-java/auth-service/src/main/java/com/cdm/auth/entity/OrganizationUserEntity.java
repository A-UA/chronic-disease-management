package com.cdm.auth.entity;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import java.io.Serializable;

@Entity
@Table(name = "organization_users")
@IdClass(OrganizationUserEntity.PK.class)
@Getter @Setter @NoArgsConstructor
public class OrganizationUserEntity {

    @Id @Column(name = "org_id")
    private Long orgId;

    @Id @Column(name = "user_id")
    private Long userId;

    @Column(name = "tenant_id", nullable = false)
    private Long tenantId;

    @Column(name = "user_type", length = 20)
    private String userType = "staff";

    @Getter @Setter @NoArgsConstructor
    public static class PK implements Serializable {
        private Long orgId;
        private Long userId;
    }
}
