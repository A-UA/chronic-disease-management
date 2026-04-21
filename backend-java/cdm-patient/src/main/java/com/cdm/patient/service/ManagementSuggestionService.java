package com.cdm.patient.service;

import com.cdm.common.security.SecurityUtils;
import com.cdm.patient.entity.ManagementSuggestionEntity;
import com.cdm.patient.repository.ManagementSuggestionRepository;
import com.cdm.patient.vo.ManagementSuggestionVo;
import com.cdm.common.util.SnowflakeIdGenerator;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class ManagementSuggestionService {
    private final ManagementSuggestionRepository repository;
    private final SnowflakeIdGenerator idGenerator;

    public ManagementSuggestionService(ManagementSuggestionRepository repository, SnowflakeIdGenerator idGenerator) {
        this.repository = repository;
        this.idGenerator = idGenerator;
    }

    public List<ManagementSuggestionVo> findAllForPatient(String patientId) {
        return repository.findAllByContextAndPatient(SecurityUtils.getTenantId(), SecurityUtils.getAllowedOrgIds(), patientId)
            .stream().map(ManagementSuggestionEntity::toVo).collect(Collectors.toList());
    }

    public ManagementSuggestionVo createSuggestion(String patientId, String suggestionType, String content) {
        ManagementSuggestionEntity entity = new ManagementSuggestionEntity();
        entity.setId(idGenerator.nextId());
        entity.setTenantId(SecurityUtils.getTenantId());
        entity.setOrgId(SecurityUtils.getOrgId());
        entity.setPatientId(patientId);
        entity.setCreatedByUserId(SecurityUtils.getUserId());
        entity.setSuggestionType(suggestionType);
        entity.setContent(content);
        entity.setStatus("active");
        entity.setCreatedAt(LocalDateTime.now());
        
        return ManagementSuggestionEntity.toVo(repository.save(entity));
    }
}
