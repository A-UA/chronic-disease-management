package com.cdm.patient.service;

import com.cdm.common.security.SecurityUtils;
import com.cdm.patient.entity.PatientManagerAssignmentEntity;
import com.cdm.patient.repository.PatientManagerAssignmentRepository;
import com.cdm.patient.vo.PatientManagerAssignmentVo;
import com.cdm.common.util.SnowflakeIdGenerator;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class PatientManagerAssignmentService {
    private final PatientManagerAssignmentRepository repository;
    private final SnowflakeIdGenerator idGenerator;

    public PatientManagerAssignmentService(PatientManagerAssignmentRepository repository, SnowflakeIdGenerator idGenerator) {
        this.repository = repository;
        this.idGenerator = idGenerator;
    }

    public List<PatientManagerAssignmentVo> findAllForPatient(String patientId) {
        return repository.findAllByContextAndPatient(SecurityUtils.getTenantId(), SecurityUtils.getAllowedOrgIds(), patientId)
            .stream().map(PatientManagerAssignmentEntity::toVo).collect(Collectors.toList());
    }

    public PatientManagerAssignmentVo assignManager(String patientId, String managerUserId, String assignmentType) {
        PatientManagerAssignmentEntity entity = new PatientManagerAssignmentEntity();
        entity.setId(idGenerator.nextId());
        entity.setTenantId(SecurityUtils.getTenantId());
        entity.setOrgId(SecurityUtils.getOrgId());
        entity.setPatientId(patientId);
        entity.setManagerUserId(managerUserId);
        entity.setAssignmentType(assignmentType);
        entity.setCreatedAt(LocalDateTime.now());
        
        return PatientManagerAssignmentEntity.toVo(repository.save(entity));
    }
}
