package com.cdm.patient.controller;

import com.cdm.common.domain.Result;
import com.cdm.patient.dto.CreateManagementSuggestionDto;
import com.cdm.patient.service.ManagementSuggestionService;
import com.cdm.patient.vo.ManagementSuggestionVo;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/management-suggestions")
@Tag(name = "Management Suggestion", description = "慢病管理建议记录")
public class ManagementSuggestionController {

    private final ManagementSuggestionService service;

    public ManagementSuggestionController(ManagementSuggestionService service) {
        this.service = service;
    }

    @Operation(summary = "获取建议列表", description = "获取特定患者的所有慢病管理建议")
    @GetMapping("/{patientId}")
    public Result<List<ManagementSuggestionVo>> getSuggestions(@PathVariable String patientId) {
        return Result.ok(service.findAllForPatient(patientId));
    }

    @Operation(summary = "新建建议", description = "由管家或医生为特定患者下发管理建议")
    @PostMapping("/{patientId}")
    public Result<ManagementSuggestionVo> createSuggestion(
            @PathVariable String patientId,
            @Valid @RequestBody CreateManagementSuggestionDto dto
    ) {
        return Result.ok(service.createSuggestion(patientId, dto.getSuggestionType(), dto.getContent()));
    }
}
