package com.cdm.auth.repository;

import com.cdm.auth.entity.PermissionEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;
import java.util.Set;

public interface PermissionRepository extends JpaRepository<PermissionEntity, String> {
    @Query("SELECT p.code FROM RoleEntity r JOIN r.permissions p WHERE r.id IN :roleIds")
    Set<String> findCodesByRoleIds(List<String> roleIds);
}
