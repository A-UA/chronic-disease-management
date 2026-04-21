package com.cdm.ai.service;

import com.cdm.ai.entity.DocumentEntity;
import com.cdm.ai.entity.KnowledgeBaseEntity;
import com.cdm.ai.repository.DocumentRepository;
import com.cdm.ai.repository.KnowledgeBaseRepository;
import com.cdm.ai.client.AgentClient;
import com.cdm.common.exception.BusinessException;
import com.cdm.common.security.SecurityUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class KnowledgeBaseService {
    
    private final KnowledgeBaseRepository kbRepository;
    private final DocumentRepository documentRepository;
    private final AgentClient agentClient;

    public KnowledgeBaseService(KnowledgeBaseRepository kbRepository, DocumentRepository documentRepository, AgentClient agentClient) {
        this.kbRepository = kbRepository;
        this.documentRepository = documentRepository;
        this.agentClient = agentClient;
    }

    @Transactional
    public void deleteKnowledgeBase(String id) {
        KnowledgeBaseEntity entity = kbRepository.findById(id)
            .orElseThrow(() -> BusinessException.notFound("Knowledge Base not found"));
        
        if (!entity.getTenantId().equals(SecurityUtils.getTenantId())) {
            throw BusinessException.forbidden("No permission to delete this knowledge base");
        }

        // 1. Delete vectors via agent
        try {
            agentClient.deleteKbVectors(id);
        } catch (Exception e) {
            // best effort
        }
        
        // 2. Delete db records of documents
        List<DocumentEntity> docs = documentRepository.findByKbId(id);
        for(DocumentEntity doc : docs) {
            documentRepository.deleteById(doc.getId());
        }

        // 3. Delete kb
        kbRepository.deleteById(id);
    }
}
