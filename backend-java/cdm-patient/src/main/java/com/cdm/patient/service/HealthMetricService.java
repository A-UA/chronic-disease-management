package com.cdm.patient.service;

import com.cdm.common.security.SecurityUtils;
import com.cdm.patient.entity.HealthMetricEntity;
import com.cdm.patient.repository.HealthMetricRepository;
import com.cdm.patient.vo.HealthMetricVo;
import com.cdm.common.util.SnowflakeIdGenerator;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class HealthMetricService {
    private final HealthMetricRepository repository;
    private final SnowflakeIdGenerator idGenerator;

    public HealthMetricService(HealthMetricRepository repository, SnowflakeIdGenerator idGenerator) {
        this.repository = repository;
        this.idGenerator = idGenerator;
    }

    public List<HealthMetricVo> findAllForPatient(String patientId) {
        return repository.findAllByContextAndPatient(SecurityUtils.getTenantId(), SecurityUtils.getAllowedOrgIds(), patientId)
            .stream().map(HealthMetricEntity::toVo).collect(Collectors.toList());
    }

    public HealthMetricVo create(String patientId, String metricType, String metricValue) {
        HealthMetricEntity entity = new HealthMetricEntity();
        entity.setId(idGenerator.nextId()); 
        entity.setTenantId(SecurityUtils.getTenantId());
        entity.setOrgId(SecurityUtils.getOrgId());
        entity.setPatientId(patientId);
        entity.setMetricType(metricType);
        entity.setMetricValue(metricValue);
        entity.setRecordedAt(LocalDateTime.now());
        
        return HealthMetricEntity.toVo(repository.save(entity));
    }
}
