package com.cdm.auth.repository;

import com.cdm.auth.entity.OrganizationUserEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;
import java.util.Optional;

public interface OrganizationUserRepository
        extends JpaRepository<OrganizationUserEntity, OrganizationUserEntity.PK> {
    List<OrganizationUserEntity> findByUserId(Long userId);
    Optional<OrganizationUserEntity> findByOrgIdAndUserId(Long orgId, Long userId);
}
