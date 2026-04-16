package com.cdm.auth.repository;

import com.cdm.auth.entity.OrganizationEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OrganizationRepository extends JpaRepository<OrganizationEntity, Long> {
    List<OrganizationEntity> findByParentId(Long parentId);
}
