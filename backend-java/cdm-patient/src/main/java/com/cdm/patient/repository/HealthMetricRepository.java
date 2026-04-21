package com.cdm.patient.repository;

import com.cdm.patient.entity.HealthMetricEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface HealthMetricRepository extends JpaRepository<HealthMetricEntity, String> {
    @Query("SELECT h FROM HealthMetricEntity h WHERE h.tenantId = :tenantId AND h.orgId IN :orgIds AND h.patientId = :patientId")
    List<HealthMetricEntity> findAllByContextAndPatient(@Param("tenantId") String tenantId, @Param("orgIds") List<String> orgIds, @Param("patientId") String patientId);
}
