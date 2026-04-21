package com.cdm.patient.repository;

import com.cdm.patient.entity.DocumentEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.List;

public interface DocumentRepository extends JpaRepository<DocumentEntity, Long> {
    List<DocumentEntity> findByKbId(Long kbId);
    Integer countByKbId(Long kbId);
}
