package com.cdm.ai.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.cdm.ai.entity.DocumentEntity;
import com.cdm.ai.entity.KnowledgeBaseEntity;
import com.cdm.ai.mapper.DocumentMapper;
import com.cdm.ai.mapper.KnowledgeBaseMapper;
import com.cdm.ai.client.AgentClient;
import com.cdm.common.exception.BusinessException;
import com.cdm.common.security.SecurityUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import java.util.List;

@Service
public class KnowledgeBaseService {
    
    private final KnowledgeBaseMapper kbMapper;
    private final DocumentMapper documentMapper;
    private final AgentClient agentClient;

    public KnowledgeBaseService(KnowledgeBaseMapper kbMapper, DocumentMapper documentMapper, AgentClient agentClient) {
        this.kbMapper = kbMapper;
        this.documentMapper = documentMapper;
        this.agentClient = agentClient;
    }

    @Transactional
    public void deleteKnowledgeBase(Long id) {
        KnowledgeBaseEntity entity = kbMapper.selectById(id);
        if (entity == null) {
            throw BusinessException.notFound("Knowledge Base not found");
        }
        
        if (!entity.getTenantId().equals(Long.parseLong(SecurityUtils.getTenantId()))) {
            throw BusinessException.forbidden("No permission to delete this knowledge base");
        }

        // 1. Delete vectors via agent
        try {
            agentClient.deleteKbVectors(id.toString());
        } catch (Exception e) {
            // best effort
        }
        
        // 2. Delete db records of documents
        List<DocumentEntity> docs = documentMapper.selectList(new LambdaQueryWrapper<DocumentEntity>()
                .eq(DocumentEntity::getKbId, id));
        for(DocumentEntity doc : docs) {
            documentMapper.deleteById(doc.getId());
        }

        // 3. Delete kb
        kbMapper.deleteById(id);
    }
}
