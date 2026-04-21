package com.cdm.auth.repository;

import com.cdm.auth.entity.OrganizationUserRoleEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface OrganizationUserRoleRepository
        extends JpaRepository<OrganizationUserRoleEntity, OrganizationUserRoleEntity.PK> {
    List<OrganizationUserRoleEntity> findByOrgIdAndUserId(String orgId, String userId);
}
