package com.cdm.ai.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.cdm.ai.dto.CreateKnowledgeBaseDto;
import com.cdm.ai.entity.DocumentEntity;
import com.cdm.ai.entity.KnowledgeBaseEntity;
import com.cdm.ai.mapper.DocumentMapper;
import com.cdm.ai.mapper.KnowledgeBaseMapper;
import com.cdm.ai.service.KnowledgeBaseService;
import com.cdm.ai.vo.KnowledgeBaseVo;
import com.cdm.common.domain.Result;
import com.cdm.common.security.SecurityUtils;
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
    
    private final KnowledgeBaseMapper kbMapper;
    private final DocumentMapper docMapper;
    private final KnowledgeBaseService kbService;

    public KnowledgeBaseController(KnowledgeBaseMapper kbMapper, DocumentMapper docMapper, KnowledgeBaseService kbService) {
        this.kbMapper = kbMapper;
        this.docMapper = docMapper;
        this.kbService = kbService;
    }

    @Operation(summary = "列出知识库", description = "获取当前租户下的所有知识库")
    @GetMapping
    public Result<List<KnowledgeBaseVo>> listKBs() {
        return Result.ok(kbMapper.selectList(new LambdaQueryWrapper<KnowledgeBaseEntity>().eq(KnowledgeBaseEntity::getTenantId, Long.parseLong(SecurityUtils.getTenantId())))
                .stream().map(KnowledgeBaseEntity::toVo).collect(Collectors.toList()));
    }

    @Operation(summary = "新建知识库", description = "为当前租户创建新的向量知识库")
    @PostMapping
    public Result<KnowledgeBaseVo> createKB(@Valid @RequestBody CreateKnowledgeBaseDto dto) {
        KnowledgeBaseEntity entity = new KnowledgeBaseEntity();
        entity.setTenantId(Long.parseLong(SecurityUtils.getTenantId()));
        entity.setOrgId(Long.parseLong(SecurityUtils.getOrgId()));
        entity.setCreatedBy(Long.parseLong(SecurityUtils.getUserId()));
        entity.setName(dto.getName());
        entity.setDescription(dto.getDescription());
        kbMapper.insert(entity);
        return Result.ok(KnowledgeBaseEntity.toVo(entity));
    }

    @Operation(summary = "查询知识库状态", description = "获取知识库中包含的文档数等统计信息")
    @GetMapping("/{id}/stats")
    public Result<Map<String, Object>> getKbStats(@PathVariable Long id) {
        Map<String, Object> stats = new HashMap<>();
        stats.put("document_count", docMapper.selectCount(new LambdaQueryWrapper<DocumentEntity>().eq(DocumentEntity::getKbId, id)));
        stats.put("chunk_count", 0); // Placeholder
        stats.put("total_tokens", 0);
        return Result.ok(stats);
    }

    @Operation(summary = "删除知识库", description = "删除指定的知识库")
    @DeleteMapping("/{id}")
    public Result<Void> deleteKb(@PathVariable Long id) {
        kbService.deleteKnowledgeBase(id);
        return Result.ok();
    }
}
