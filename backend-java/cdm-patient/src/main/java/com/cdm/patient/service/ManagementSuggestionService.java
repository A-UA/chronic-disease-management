package com.cdm.patient.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.cdm.common.security.SecurityUtils;
import com.cdm.patient.entity.ManagementSuggestionEntity;
import com.cdm.patient.mapper.ManagementSuggestionMapper;
import com.cdm.patient.vo.ManagementSuggestionVo;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;
import java.util.stream.Collectors;

@Service
public class ManagementSuggestionService {
    private final ManagementSuggestionMapper mapper;

    public ManagementSuggestionService(ManagementSuggestionMapper mapper) {
        this.mapper = mapper;
    }

    public List<ManagementSuggestionVo> findAllForPatient(Long patientId) {
        Long tenantId = Long.parseLong(SecurityUtils.getTenantId());
        List<Long> orgIds = SecurityUtils.getAllowedOrgIds().stream().map(Long::parseLong).collect(Collectors.toList());
        return mapper.selectList(new LambdaQueryWrapper<ManagementSuggestionEntity>()
                .eq(ManagementSuggestionEntity::getTenantId, tenantId)
                .in(ManagementSuggestionEntity::getOrgId, orgIds)
                .eq(ManagementSuggestionEntity::getPatientId, patientId))
            .stream().map(ManagementSuggestionEntity::toVo).collect(Collectors.toList());
    }

    public ManagementSuggestionVo createSuggestion(Long patientId, String suggestionType, String content) {
        ManagementSuggestionEntity entity = new ManagementSuggestionEntity();
        entity.setTenantId(Long.parseLong(SecurityUtils.getTenantId()));
        entity.setOrgId(Long.parseLong(SecurityUtils.getOrgId()));
        entity.setPatientId(patientId);
        entity.setCreatedByUserId(Long.parseLong(SecurityUtils.getUserId()));
        entity.setSuggestionType(suggestionType);
        entity.setContent(content);
        entity.setStatus("active");
        entity.setCreatedAt(LocalDateTime.now());
        
        mapper.insert(entity);
        return ManagementSuggestionEntity.toVo(entity);
    }
}
