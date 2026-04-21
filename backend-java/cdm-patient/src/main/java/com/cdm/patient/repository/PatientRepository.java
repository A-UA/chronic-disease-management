package com.cdm.patient.repository;

import com.cdm.patient.entity.PatientProfileEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface PatientRepository extends JpaRepository<PatientProfileEntity, Long> {
    @Query("SELECT p FROM PatientProfileEntity p WHERE p.tenantId = :tenantId AND p.orgId IN :orgIds")
    List<PatientProfileEntity> findAllByContext(@Param("tenantId") Long tenantId, @Param("orgIds") List<Long> orgIds);
}
