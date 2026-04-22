package com.cdm.patient.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.cdm.common.security.SecurityUtils;
import com.cdm.patient.entity.PatientProfileEntity;
import com.cdm.patient.mapper.PatientMapper;
import com.cdm.patient.vo.PatientVo;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.stream.Collectors;

@Service
public class PatientService {
    private final PatientMapper mapper;

    public PatientService(PatientMapper mapper) {
        this.mapper = mapper;
    }

    public List<PatientVo> findAll() {
        Long tenantId = Long.parseLong(SecurityUtils.getTenantId());
        List<Long> orgIds = SecurityUtils.getAllowedOrgIds().stream().map(Long::parseLong).collect(Collectors.toList());
        var entities = mapper.selectList(new LambdaQueryWrapper<PatientProfileEntity>()
                .eq(PatientProfileEntity::getTenantId, tenantId)
                .in(PatientProfileEntity::getOrgId, orgIds));
        return entities.stream().map(PatientProfileEntity::toVo).collect(Collectors.toList());
    }

    public PatientVo createPatient(String name, String gender) {
        PatientProfileEntity entity = new PatientProfileEntity();
        entity.setTenantId(Long.parseLong(SecurityUtils.getTenantId()));
        entity.setOrgId(Long.parseLong(SecurityUtils.getOrgId()));
        entity.setName(name);
        entity.setGender(gender);
        
        mapper.insert(entity);
        return PatientProfileEntity.toVo(entity);
    }
}
