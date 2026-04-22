package com.cdm.patient.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.cdm.common.security.SecurityUtils;
import com.cdm.patient.entity.HealthMetricEntity;
import com.cdm.patient.mapper.HealthMetricMapper;
import com.cdm.patient.vo.HealthMetricVo;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class HealthMetricService {
    private final HealthMetricMapper mapper;

    public HealthMetricService(HealthMetricMapper mapper) {
        this.mapper = mapper;
    }

    public List<HealthMetricVo> findAllForPatient(Long patientId) {
        Long tenantId = Long.parseLong(SecurityUtils.getTenantId());
        List<Long> orgIds = SecurityUtils.getAllowedOrgIds().stream().map(Long::parseLong).collect(Collectors.toList());
        return mapper.selectList(new LambdaQueryWrapper<HealthMetricEntity>()
                .eq(HealthMetricEntity::getTenantId, tenantId)
                .in(HealthMetricEntity::getOrgId, orgIds)
                .eq(HealthMetricEntity::getPatientId, patientId))
            .stream().map(HealthMetricEntity::toVo).collect(Collectors.toList());
    }

    public HealthMetricVo create(Long patientId, String metricType, String metricValue) {
        HealthMetricEntity entity = new HealthMetricEntity();
        entity.setTenantId(Long.parseLong(SecurityUtils.getTenantId()));
        entity.setOrgId(Long.parseLong(SecurityUtils.getOrgId()));
        entity.setPatientId(patientId);
        entity.setMetricType(metricType);
        entity.setMetricValue(metricValue);
        entity.setRecordedAt(LocalDateTime.now());
        
        mapper.insert(entity);
        return HealthMetricEntity.toVo(entity);
    }
}
