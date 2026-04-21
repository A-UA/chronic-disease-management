package com.cdm.ai.controller;

import com.cdm.ai.dto.CreateKnowledgeBaseDto;
import com.cdm.ai.entity.KnowledgeBaseEntity;
import com.cdm.ai.repository.DocumentRepository;
import com.cdm.ai.repository.KnowledgeBaseRepository;
import com.cdm.ai.vo.KnowledgeBaseVo;
import com.cdm.common.domain.Result;
import com.cdm.common.security.SecurityUtils;
import com.cdm.common.util.SnowflakeIdGenerator;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/v1/kb")
@Tag(name = "Knowledge Base", description = "AI 知识库管理")
public class KnowledgeBaseController {
    
    private final KnowledgeBaseRepository kbRepo;
    private final DocumentRepository docRepo;
    private final SnowflakeIdGenerator idGenerator;

    public KnowledgeBaseController(KnowledgeBaseRepository kbRepo, DocumentRepository docRepo, SnowflakeIdGenerator idGenerator) {
        this.kbRepo = kbRepo;
        this.docRepo = docRepo;
        this.idGenerator = idGenerator;
    }

    @Operation(summary = "列出知识库", description = "获取当前租户下的所有知识库")
    @GetMapping
    public Result<List<KnowledgeBaseVo>> listKBs() {
        return Result.ok(kbRepo.findByTenantId(SecurityUtils.getTenantId())
                .stream().map(KnowledgeBaseEntity::toVo).collect(Collectors.toList()));
    }

    @Operation(summary = "新建知识库", description = "为当前租户创建新的向量知识库")
    @PostMapping
    public Result<KnowledgeBaseVo> createKB(@Valid @RequestBody CreateKnowledgeBaseDto dto) {
        KnowledgeBaseEntity entity = new KnowledgeBaseEntity();
        entity.setId(idGenerator.nextId());
        entity.setTenantId(SecurityUtils.getTenantId());
        entity.setOrgId(SecurityUtils.getOrgId());
        entity.setCreatedBy(SecurityUtils.getUserId());
        entity.setName(dto.getName());
        entity.setDescription(dto.getDescription());
        return Result.ok(KnowledgeBaseEntity.toVo(kbRepo.save(entity)));
    }

    @Operation(summary = "查询知识库状态", description = "获取知识库中包含的文档数等统计信息")
    @GetMapping("/{id}/stats")
    public Result<Map<String, Object>> getKbStats(@PathVariable String id) {
        Map<String, Object> stats = new HashMap<>();
        stats.put("document_count", docRepo.countByKbId(id));
        stats.put("chunk_count", 0); // Placeholder
        stats.put("total_tokens", 0);
        return Result.ok(stats);
    }

    @Operation(summary = "删除知识库", description = "删除指定的知识库")
    @DeleteMapping("/{id}")
    public Result<Void> deleteKb(@PathVariable String id) {
        kbRepo.deleteById(id);
        return Result.ok();
    }
}
