package com.cdm.patient.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.cdm.common.security.SecurityUtils;
import com.cdm.patient.entity.PatientManagerAssignmentEntity;
import com.cdm.patient.mapper.PatientManagerAssignmentMapper;
import com.cdm.patient.vo.PatientManagerAssignmentVo;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class PatientManagerAssignmentService {
    private final PatientManagerAssignmentMapper mapper;

    public PatientManagerAssignmentService(PatientManagerAssignmentMapper mapper) {
        this.mapper = mapper;
    }

    public List<PatientManagerAssignmentVo> findAllForPatient(Long patientId) {
        Long tenantId = Long.parseLong(SecurityUtils.getTenantId());
        List<Long> orgIds = SecurityUtils.getAllowedOrgIds().stream().map(Long::parseLong).collect(Collectors.toList());
        return mapper.selectList(new LambdaQueryWrapper<PatientManagerAssignmentEntity>()
                .eq(PatientManagerAssignmentEntity::getTenantId, tenantId)
                .in(PatientManagerAssignmentEntity::getOrgId, orgIds)
                .eq(PatientManagerAssignmentEntity::getPatientId, patientId))
            .stream().map(PatientManagerAssignmentEntity::toVo).collect(Collectors.toList());
    }

    public PatientManagerAssignmentVo assignManager(Long patientId, Long managerUserId, String assignmentType) {
        PatientManagerAssignmentEntity entity = new PatientManagerAssignmentEntity();
        entity.setTenantId(Long.parseLong(SecurityUtils.getTenantId()));
        entity.setOrgId(Long.parseLong(SecurityUtils.getOrgId()));
        entity.setPatientId(patientId);
        entity.setManagerUserId(managerUserId);
        entity.setAssignmentType(assignmentType);
        entity.setCreatedAt(LocalDateTime.now());
        
        mapper.insert(entity);
        return PatientManagerAssignmentEntity.toVo(entity);
    }
}
