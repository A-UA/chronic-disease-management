package com.cdm.auth.repository;

import com.cdm.auth.entity.RoleEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface RoleRepository extends JpaRepository<RoleEntity, String> {
    Optional<RoleEntity> findByCodeAndTenantIdIsNull(String code);
}
