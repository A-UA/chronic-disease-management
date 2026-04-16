package com.cdm.patient.controller;

import com.cdm.patient.entity.DocumentEntity;
import com.cdm.patient.repository.DocumentRepository;
import com.cdm.patient.service.MinioService;
import com.cdm.patient.client.AgentClient;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.util.List;

@RestController
@RequestMapping("/api/v1/documents")
public class DocumentController {
    
    private final DocumentRepository docRepo;
    private final MinioService minioService;
    private final AgentClient agentClient;

    public DocumentController(DocumentRepository docRepo, MinioService minioService, AgentClient agentClient) {
        this.docRepo = docRepo;
        this.minioService = minioService;
        this.agentClient = agentClient;
    }

    @GetMapping("/kb/{kbId}/documents")
    public List<DocumentEntity> listDocuments(@PathVariable Long kbId) {
        return docRepo.findByKbId(kbId);
    }

    @PostMapping("/kb/{kbId}/documents")
    public DocumentEntity uploadDocument(@PathVariable Long kbId, @RequestParam("file") MultipartFile file) throws Exception {
        // Upload to minio
        String minioUrl = minioService.uploadFile(file);

        // Save DB processing
        DocumentEntity entity = new DocumentEntity();
        entity.setTenantId(1L);
        entity.setKbId(kbId);
        entity.setOrgId(1L);
        entity.setUploaderId(1L);
        entity.setFileName(file.getOriginalFilename());
        entity.setFileSize((int) file.getSize());
        entity.setFileType(file.getContentType());
        entity.setMinioUrl(minioUrl);
        entity.setStatus("processing");
        entity = docRepo.save(entity);

        // Send to agent parsing pipeline
        int chunks = agentClient.parseDocument(file, kbId);
        entity.setChunkCount(chunks);
        entity.setStatus(chunks > 0 ? "completed" : "failed");
        return docRepo.save(entity);
    }

    @DeleteMapping("/{id}")
    public void deleteDocument(@PathVariable Long id) {
        docRepo.deleteById(id);
    }
}
