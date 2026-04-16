package com.cdm.auth.repository;

import com.cdm.auth.entity.PermissionEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;
import java.util.Set;

public interface PermissionRepository extends JpaRepository<PermissionEntity, Long> {
    @Query("SELECT p.code FROM PermissionEntity p JOIN p.roles r WHERE r.id IN :roleIds")
    Set<String> findCodesByRoleIds(List<Long> roleIds);
}
