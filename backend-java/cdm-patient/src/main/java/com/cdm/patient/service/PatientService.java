package com.cdm.patient.service;

import com.cdm.common.security.SecurityUtils;
import com.cdm.patient.entity.PatientProfileEntity;
import com.cdm.patient.repository.PatientRepository;
import com.cdm.patient.vo.PatientVo;
import com.cdm.common.util.SnowflakeIdGenerator;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class PatientService {
    private final PatientRepository repository;
    private final SnowflakeIdGenerator idGenerator;

    public PatientService(PatientRepository repository, SnowflakeIdGenerator idGenerator) {
        this.repository = repository;
        this.idGenerator = idGenerator;
    }

    public List<PatientVo> findAll() {
        var entities = repository.findAllByContext(SecurityUtils.getTenantId(), SecurityUtils.getAllowedOrgIds());
        return entities.stream().map(PatientProfileEntity::toVo).collect(Collectors.toList());
    }

    public PatientVo createPatient(String name, String gender) {
        PatientProfileEntity entity = new PatientProfileEntity();
        entity.setId(idGenerator.nextId());
        entity.setTenantId(SecurityUtils.getTenantId());
        entity.setOrgId(SecurityUtils.getOrgId());
        entity.setName(name);
        entity.setGender(gender);
        return PatientProfileEntity.toVo(repository.save(entity));
    }
}
