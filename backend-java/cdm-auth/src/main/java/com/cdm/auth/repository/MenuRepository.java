package com.cdm.auth.repository;

import com.cdm.auth.entity.MenuEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.List;

public interface MenuRepository extends JpaRepository<MenuEntity, Long> {
    @Query("SELECT m FROM MenuEntity m WHERE m.isEnabled = true " +
           "AND (m.tenantId IS NULL OR m.tenantId = :tenantId) ORDER BY m.sort ASC")
    List<MenuEntity> findActiveMenus(Long tenantId);
}
