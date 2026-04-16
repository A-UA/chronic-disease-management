package com.cdm.patient.controller;

import com.cdm.patient.entity.KnowledgeBaseEntity;
import com.cdm.patient.repository.DocumentRepository;
import com.cdm.patient.repository.KnowledgeBaseRepository;
import org.springframework.web.bind.annotation.*;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/kb")
public class KnowledgeBaseController {
    private final KnowledgeBaseRepository kbRepo;
    private final DocumentRepository docRepo;

    public KnowledgeBaseController(KnowledgeBaseRepository kbRepo, DocumentRepository docRepo) {
        this.kbRepo = kbRepo;
        this.docRepo = docRepo;
    }

    @GetMapping
    public List<KnowledgeBaseEntity> listKBs() {
        return kbRepo.findByTenantId(1L);
    }

    @PostMapping
    public KnowledgeBaseEntity createKB(@RequestBody KnowledgeBaseEntity entity) {
        entity.setTenantId(1L);
        entity.setOrgId(1L);
        entity.setCreatedBy(1L);
        return kbRepo.save(entity);
    }

    @GetMapping("/{id}/stats")
    public Map<String, Object> getKbStats(@PathVariable Long id) {
        Map<String, Object> stats = new HashMap<>();
        stats.put("document_count", docRepo.countByKbId(id));
        stats.put("chunk_count", 0); // Placeholder until chunk table is present
        stats.put("total_tokens", 0);
        return stats;
    }

    @DeleteMapping("/{id}")
    public void deleteKb(@PathVariable Long id) {
        kbRepo.deleteById(id);
    }
}
