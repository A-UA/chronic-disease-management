package com.cdm.patient.service;

import com.cdm.common.security.IdentityPayload;
import com.cdm.patient.entity.ManagementSuggestionEntity;
import com.cdm.patient.repository.ManagementSuggestionRepository;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class ManagementSuggestionService {
    private final ManagementSuggestionRepository repository;

    public ManagementSuggestionService(ManagementSuggestionRepository repository) {
        this.repository = repository;
    }

    public List<ManagementSuggestionEntity> findAllForPatient(IdentityPayload identity, Long patientId) {
        return repository.findAllByContextAndPatient(identity.getTenantId(), identity.getAllowedOrgIds(), patientId);
    }

    public ManagementSuggestionEntity createSuggestion(IdentityPayload identity, Long patientId, String suggestionType, String content) {
        ManagementSuggestionEntity entity = new ManagementSuggestionEntity();
        entity.setId(System.currentTimeMillis());
        entity.setTenantId(identity.getTenantId());
        entity.setOrgId(identity.getOrgId());
        entity.setPatientId(patientId);
        entity.setCreatedByUserId(identity.getUserId());
        entity.setSuggestionType(suggestionType);
        entity.setContent(content);
        entity.setStatus("active");
        entity.setCreatedAt(LocalDateTime.now());
        
        return repository.save(entity);
    }
}
