package com.cdm.patient.repository;

import com.cdm.patient.entity.PatientManagerAssignmentEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface PatientManagerAssignmentRepository extends JpaRepository<PatientManagerAssignmentEntity, Long> {
    @Query("SELECT a FROM PatientManagerAssignmentEntity a WHERE a.tenantId = :tenantId AND a.orgId IN :orgIds AND a.patientId = :patientId")
    List<PatientManagerAssignmentEntity> findAllByContextAndPatient(@Param("tenantId") Long tenantId, @Param("orgIds") List<Long> orgIds, @Param("patientId") Long patientId);
}
