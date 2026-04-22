package com.cdm.ai.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.cdm.ai.entity.DocumentEntity;
import com.cdm.ai.mapper.DocumentMapper;
import com.cdm.ai.service.MinioService;
import com.cdm.ai.client.AgentClient;
import com.cdm.ai.service.DocumentService;
import com.cdm.ai.vo.DocumentVo;
import com.cdm.common.domain.Result;
import com.cdm.common.security.SecurityUtils;
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
    
    private final DocumentMapper docMapper;
    private final MinioService minioService;
    private final AgentClient agentClient;
    private final DocumentService documentService;

    public DocumentController(DocumentMapper docMapper, MinioService minioService, AgentClient agentClient, DocumentService documentService) {
        this.docMapper = docMapper;
        this.minioService = minioService;
        this.agentClient = agentClient;
        this.documentService = documentService;
    }

    @Operation(summary = "列出文档", description = "获取特定知识库下的所有文档")
    @GetMapping("/kb/{kbId}/documents")
    public Result<List<DocumentVo>> listDocuments(@PathVariable Long kbId) {
        return Result.ok(docMapper.selectList(new LambdaQueryWrapper<DocumentEntity>().eq(DocumentEntity::getKbId, kbId))
                .stream().map(DocumentEntity::toVo).collect(Collectors.toList()));
    }

    @Operation(summary = "上传解析文档", description = "上传文档到 MinIO 并调用 Agent 提取向量")
    @PostMapping("/kb/{kbId}/documents")
    public Result<DocumentVo> uploadDocument(@PathVariable Long kbId, @RequestParam("file") MultipartFile file) throws Exception {
        // Upload to minio
        String minioUrl = minioService.uploadFile(file);

        // Save DB processing
        DocumentEntity entity = new DocumentEntity();
        entity.setTenantId(Long.parseLong(SecurityUtils.getTenantId()));
        entity.setKbId(kbId);
        entity.setOrgId(Long.parseLong(SecurityUtils.getOrgId()));
        entity.setUploaderId(Long.parseLong(SecurityUtils.getUserId()));
        entity.setFileName(file.getOriginalFilename());
        entity.setFileSize((int) file.getSize());
        entity.setFileType(file.getContentType());
        entity.setMinioUrl(minioUrl);
        entity.setStatus("processing");
        docMapper.insert(entity);

        // Send to agent parsing pipeline
        var feignResult = agentClient.parseDocument(file, kbId.toString());
        int chunks = 0;
        if (feignResult != null && feignResult.containsKey("chunk_count")) {
            chunks = (Integer) feignResult.get("chunk_count");
        }
        
        entity.setChunkCount(chunks);
        entity.setStatus(chunks > 0 ? "completed" : "failed");
        docMapper.updateById(entity);
        return Result.ok(DocumentEntity.toVo(entity));
    }

    @Operation(summary = "删除文档", description = "删除知识库中包含的该文档记录")
    @DeleteMapping("/{id}")
    public Result<Void> deleteDocument(@PathVariable Long id) {
        documentService.deleteDocument(id);
        return Result.ok();
    }
}
