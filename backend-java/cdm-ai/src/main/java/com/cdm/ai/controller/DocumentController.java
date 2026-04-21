package com.cdm.ai.controller;

import com.cdm.ai.entity.DocumentEntity;
import com.cdm.ai.repository.DocumentRepository;
import com.cdm.ai.service.MinioService;
import com.cdm.ai.client.AgentClient;
import com.cdm.ai.service.DocumentService;
import com.cdm.ai.vo.DocumentVo;
import com.cdm.common.domain.Result;
import com.cdm.common.security.SecurityUtils;
import com.cdm.common.util.SnowflakeIdGenerator;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.util.List;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/v1/documents")
@Tag(name = "Document", description = "AI 知识库文档管理")
public class DocumentController {
    
    private final DocumentRepository docRepo;
    private final MinioService minioService;
    private final AgentClient agentClient;
    private final SnowflakeIdGenerator idGenerator;

    private final DocumentService documentService;

    public DocumentController(DocumentRepository docRepo, MinioService minioService, AgentClient agentClient, SnowflakeIdGenerator idGenerator, DocumentService documentService) {
        this.docRepo = docRepo;
        this.minioService = minioService;
        this.agentClient = agentClient;
        this.idGenerator = idGenerator;
        this.documentService = documentService;
    }

    @Operation(summary = "列出文档", description = "获取特定知识库下的所有文档")
    @GetMapping("/kb/{kbId}/documents")
    public Result<List<DocumentVo>> listDocuments(@PathVariable String kbId) {
        return Result.ok(docRepo.findByKbId(kbId)
                .stream().map(DocumentEntity::toVo).collect(Collectors.toList()));
    }

    @Operation(summary = "上传解析文档", description = "上传文档到 MinIO 并调用 Agent 提取向量")
    @PostMapping("/kb/{kbId}/documents")
    public Result<DocumentVo> uploadDocument(@PathVariable String kbId, @RequestParam("file") MultipartFile file) throws Exception {
        // Upload to minio
        String minioUrl = minioService.uploadFile(file);

        // Save DB processing
        DocumentEntity entity = new DocumentEntity();
        entity.setId(idGenerator.nextId());
        entity.setTenantId(SecurityUtils.getTenantId());
        entity.setKbId(kbId);
        entity.setOrgId(SecurityUtils.getOrgId());
        entity.setUploaderId(SecurityUtils.getUserId());
        entity.setFileName(file.getOriginalFilename());
        entity.setFileSize((int) file.getSize());
        entity.setFileType(file.getContentType());
        entity.setMinioUrl(minioUrl);
        entity.setStatus("processing");
        entity = docRepo.save(entity);

        // Send to agent parsing pipeline
        var feignResult = agentClient.parseDocument(file, kbId);
        int chunks = 0;
        if (feignResult != null && feignResult.containsKey("chunk_count")) {
            chunks = (Integer) feignResult.get("chunk_count");
        }
        
        entity.setChunkCount(chunks);
        entity.setStatus(chunks > 0 ? "completed" : "failed");
        return Result.ok(DocumentEntity.toVo(docRepo.save(entity)));
    }

    @Operation(summary = "删除文档", description = "删除知识库中包含的该文档记录")
    @DeleteMapping("/{id}")
    public Result<Void> deleteDocument(@PathVariable String id) {
        documentService.deleteDocument(id);
        return Result.ok();
    }
}
