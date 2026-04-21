package com.cdm.patient.repository;

import com.cdm.patient.entity.KnowledgeBaseEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface KnowledgeBaseRepository extends JpaRepository<KnowledgeBaseEntity, Long> {
    List<KnowledgeBaseEntity> findByTenantId(Long tenantId);
}
