package com.cdm.auth.repository;

import com.cdm.auth.entity.OrganizationUserEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface OrganizationUserRepository
        extends JpaRepository<OrganizationUserEntity, OrganizationUserEntity.PK> {
    List<OrganizationUserEntity> findByUserId(String userId);
    Optional<OrganizationUserEntity> findByOrgIdAndUserId(String orgId, String userId);
}
