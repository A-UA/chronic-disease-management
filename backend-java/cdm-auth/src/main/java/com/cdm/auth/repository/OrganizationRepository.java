package com.cdm.auth.repository;

import com.cdm.auth.entity.OrganizationEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OrganizationRepository extends JpaRepository<OrganizationEntity, String> {
    List<OrganizationEntity> findByParentId(String parentId);
}
