package com.cdm.patient.repository;

import com.cdm.patient.entity.ManagementSuggestionEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface ManagementSuggestionRepository extends JpaRepository<ManagementSuggestionEntity, String> {
    @Query("SELECT s FROM ManagementSuggestionEntity s WHERE s.tenantId = :tenantId AND s.orgId IN :orgIds AND s.patientId = :patientId")
    List<ManagementSuggestionEntity> findAllByContextAndPatient(@Param("tenantId") String tenantId, @Param("orgIds") List<String> orgIds, @Param("patientId") String patientId);
}
