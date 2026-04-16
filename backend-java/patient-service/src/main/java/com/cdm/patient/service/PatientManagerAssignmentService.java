package com.cdm.patient.service;

import com.cdm.common.security.IdentityPayload;
import com.cdm.patient.entity.PatientManagerAssignmentEntity;
import com.cdm.patient.repository.PatientManagerAssignmentRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class PatientManagerAssignmentService {
    private final PatientManagerAssignmentRepository repository;

    public PatientManagerAssignmentService(PatientManagerAssignmentRepository repository) {
        this.repository = repository;
    }

    public List<PatientManagerAssignmentEntity> findAllForPatient(IdentityPayload identity, Long patientId) {
        return repository.findAllByContextAndPatient(identity.getTenantId(), identity.getAllowedOrgIds(), patientId);
    }

    public PatientManagerAssignmentEntity assignManager(IdentityPayload identity, Long patientId, Long managerUserId, String assignmentType) {
        PatientManagerAssignmentEntity entity = new PatientManagerAssignmentEntity();
        entity.setId(System.currentTimeMillis());
        entity.setTenantId(identity.getTenantId());
        entity.setOrgId(identity.getOrgId());
        entity.setPatientId(patientId);
        entity.setManagerUserId(managerUserId);
        entity.setAssignmentType(assignmentType);
        entity.setCreatedAt(LocalDateTime.now());
        
        return repository.save(entity);
    }
}
