package com.cdm.patient.service;

import com.cdm.common.security.SecurityUtils;
import com.cdm.patient.entity.PatientFamilyLinkEntity;
import com.cdm.patient.repository.PatientFamilyLinkRepository;
import com.cdm.patient.vo.PatientFamilyLinkVo;
import com.cdm.common.util.SnowflakeIdGenerator;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class PatientFamilyLinkService {
    private final PatientFamilyLinkRepository repository;
    private final SnowflakeIdGenerator idGenerator;

    public PatientFamilyLinkService(PatientFamilyLinkRepository repository, SnowflakeIdGenerator idGenerator) {
        this.repository = repository;
        this.idGenerator = idGenerator;
    }

    public List<PatientFamilyLinkVo> findAllForPatient(String patientId) {
        return repository.findAllByContextAndPatient(SecurityUtils.getTenantId(), SecurityUtils.getAllowedOrgIds(), patientId)
            .stream().map(PatientFamilyLinkEntity::toVo).collect(Collectors.toList());
    }

    public PatientFamilyLinkVo linkFamily(String patientId, String familyUserId, String relationship) {
        PatientFamilyLinkEntity entity = new PatientFamilyLinkEntity();
        entity.setId(idGenerator.nextId());
        entity.setTenantId(SecurityUtils.getTenantId());
        entity.setOrgId(SecurityUtils.getOrgId());
        entity.setPatientId(patientId);
        entity.setFamilyUserId(familyUserId);
        entity.setRelationship(relationship);
        entity.setCreatedAt(LocalDateTime.now());
        
        return PatientFamilyLinkEntity.toVo(repository.save(entity));
    }
}
