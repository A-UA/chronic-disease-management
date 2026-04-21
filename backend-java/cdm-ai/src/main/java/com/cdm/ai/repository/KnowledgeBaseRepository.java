package com.cdm.ai.repository;

import com.cdm.ai.entity.KnowledgeBaseEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface KnowledgeBaseRepository extends JpaRepository<KnowledgeBaseEntity, String> {
    List<KnowledgeBaseEntity> findByTenantId(String tenantId);
}
