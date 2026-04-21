package com.cdm.patient.repository;

import com.cdm.patient.entity.PatientFamilyLinkEntity;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface PatientFamilyLinkRepository extends JpaRepository<PatientFamilyLinkEntity, Long> {
    @Query("SELECT l FROM PatientFamilyLinkEntity l WHERE l.tenantId = :tenantId AND l.orgId IN :orgIds AND l.patientId = :patientId")
    List<PatientFamilyLinkEntity> findAllByContextAndPatient(@Param("tenantId") Long tenantId, @Param("orgIds") List<Long> orgIds, @Param("patientId") Long patientId);
}
