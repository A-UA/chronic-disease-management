package com.cdm.patient.service;

import com.cdm.common.security.IdentityPayload;
import com.cdm.patient.entity.PatientFamilyLinkEntity;
import com.cdm.patient.repository.PatientFamilyLinkRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class PatientFamilyLinkService {
    private final PatientFamilyLinkRepository repository;

    public PatientFamilyLinkService(PatientFamilyLinkRepository repository) {
        this.repository = repository;
    }

    public List<PatientFamilyLinkEntity> findAllForPatient(IdentityPayload identity, Long patientId) {
        return repository.findAllByContextAndPatient(identity.getTenantId(), identity.getAllowedOrgIds(), patientId);
    }

    public PatientFamilyLinkEntity linkFamily(IdentityPayload identity, Long patientId, Long familyUserId, String relationship) {
        PatientFamilyLinkEntity entity = new PatientFamilyLinkEntity();
        entity.setId(com.cdm.common.util.SnowflakeIdGenerator.nextId());
        entity.setTenantId(identity.getTenantId());
        entity.setOrgId(identity.getOrgId());
        entity.setPatientId(patientId);
        entity.setFamilyUserId(familyUserId);
        entity.setRelationship(relationship);
        entity.setCreatedAt(LocalDateTime.now());
        
        return repository.save(entity);
    }
}
