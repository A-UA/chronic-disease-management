package com.cdm.patient.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.cdm.common.security.SecurityUtils;
import com.cdm.patient.entity.PatientFamilyLinkEntity;
import com.cdm.patient.mapper.PatientFamilyLinkMapper;
import com.cdm.patient.vo.PatientFamilyLinkVo;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class PatientFamilyLinkService {
    private final PatientFamilyLinkMapper mapper;

    public PatientFamilyLinkService(PatientFamilyLinkMapper mapper) {
        this.mapper = mapper;
    }

    public List<PatientFamilyLinkVo> findAllForPatient(Long patientId) {
        Long tenantId = Long.parseLong(SecurityUtils.getTenantId());
        List<Long> orgIds = SecurityUtils.getAllowedOrgIds().stream().map(Long::parseLong).collect(Collectors.toList());
        return mapper.selectList(new LambdaQueryWrapper<PatientFamilyLinkEntity>()
                .eq(PatientFamilyLinkEntity::getTenantId, tenantId)
                .in(PatientFamilyLinkEntity::getOrgId, orgIds)
                .eq(PatientFamilyLinkEntity::getPatientId, patientId))
            .stream().map(PatientFamilyLinkEntity::toVo).collect(Collectors.toList());
    }

    public PatientFamilyLinkVo linkFamily(Long patientId, Long familyUserId, String relationship) {
        PatientFamilyLinkEntity entity = new PatientFamilyLinkEntity();
        entity.setTenantId(Long.parseLong(SecurityUtils.getTenantId()));
        entity.setOrgId(Long.parseLong(SecurityUtils.getOrgId()));
        entity.setPatientId(patientId);
        entity.setFamilyUserId(familyUserId);
        entity.setRelationship(relationship);
        entity.setCreatedAt(LocalDateTime.now());
        
        mapper.insert(entity);
        return PatientFamilyLinkEntity.toVo(entity);
    }
}
