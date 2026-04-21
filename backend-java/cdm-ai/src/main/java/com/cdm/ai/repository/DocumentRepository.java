package com.cdm.ai.repository;

import com.cdm.ai.entity.DocumentEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface DocumentRepository extends JpaRepository<DocumentEntity, String> {
    List<DocumentEntity> findByKbId(String kbId);
    Integer countByKbId(String kbId);
}
