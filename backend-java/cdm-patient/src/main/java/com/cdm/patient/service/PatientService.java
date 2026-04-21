package com.cdm.patient.service;

import com.cdm.common.security.IdentityPayload;
import com.cdm.patient.entity.PatientProfileEntity;
import com.cdm.patient.repository.PatientRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PatientService {
    private final PatientRepository repository;

    public PatientService(PatientRepository repository) {
        this.repository = repository;
    }

    public List<PatientProfileEntity> findAll(IdentityPayload identity) {
        return repository.findAllByContext(identity.getTenantId(), identity.getAllowedOrgIds());
    }

    public PatientProfileEntity createPatient(IdentityPayload identity, String name, String gender) {
        PatientProfileEntity entity = new PatientProfileEntity();
        entity.setId(com.cdm.common.util.SnowflakeIdGenerator.nextId());
        entity.setTenantId(identity.getTenantId());
        entity.setOrgId(identity.getOrgId());
        entity.setName(name);
        entity.setGender(gender);
        return repository.save(entity);
    }
}
