package com.cdm.ai.service;

import com.cdm.ai.entity.DocumentEntity;
import com.cdm.ai.repository.DocumentRepository;
import com.cdm.ai.client.AgentClient;
import com.cdm.common.exception.BusinessException;
import com.cdm.common.security.SecurityUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class DocumentService {
    
    private final DocumentRepository documentRepository;
    private final AgentClient agentClient;

    public DocumentService(DocumentRepository documentRepository, AgentClient agentClient) {
        this.documentRepository = documentRepository;
        this.agentClient = agentClient;
    }

    @Transactional
    public void deleteDocument(String id) {
        DocumentEntity entity = documentRepository.findById(id)
            .orElseThrow(() -> BusinessException.notFound("Document not found"));
        
        // 权限校验
        if (!entity.getTenantId().equals(SecurityUtils.getTenantId())) {
            throw BusinessException.forbidden("No permission to delete this document");
        }

        // 1. Delete vectors via agent
        try {
            agentClient.deleteDocVectors(entity.getKbId(), entity.getFileName());
        } catch (Exception e) {
            // Logs and proceed (best effort)
        }
        
        // 2. Delete db record
        documentRepository.deleteById(id);
    }
}
