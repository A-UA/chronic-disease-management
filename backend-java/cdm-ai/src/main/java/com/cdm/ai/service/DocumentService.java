package com.cdm.ai.service;

import com.cdm.ai.entity.DocumentEntity;
import com.cdm.ai.mapper.DocumentMapper;
import com.cdm.ai.client.AgentClient;
import com.cdm.common.exception.BusinessException;
import com.cdm.common.security.SecurityUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DocumentService {
    
    private final DocumentMapper documentMapper;
    private final AgentClient agentClient;

    public DocumentService(DocumentMapper documentMapper, AgentClient agentClient) {
        this.documentMapper = documentMapper;
        this.agentClient = agentClient;
    }

    @Transactional
    public void deleteDocument(Long id) {
        DocumentEntity entity = documentMapper.selectById(id);
        if (entity == null) {
            throw BusinessException.notFound("Document not found");
        }
        
        // 权限校验
        if (!entity.getTenantId().equals(Long.parseLong(SecurityUtils.getTenantId()))) {
            throw BusinessException.forbidden("No permission to delete this document");
        }

        // 1. Delete vectors via agent
        try {
            agentClient.deleteDocVectors(entity.getKbId().toString(), entity.getFileName());
        } catch (Exception e) {
            // Logs and proceed (best effort)
        }
        
        // 2. Delete db record
        documentMapper.deleteById(id);
    }
}
