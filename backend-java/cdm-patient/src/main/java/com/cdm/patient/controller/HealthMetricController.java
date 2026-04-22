package com.cdm.patient.controller;

import com.cdm.common.domain.Result;
import com.cdm.patient.dto.CreateHealthMetricDto;
import com.cdm.patient.service.HealthMetricService;
import com.cdm.patient.vo.HealthMetricVo;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/health-metrics")
@Tag(name = "Health Metric", description = "健康指标记录")
public class HealthMetricController {

    private final HealthMetricService service;

    public HealthMetricController(HealthMetricService service) {
        this.service = service;
    }

    @Operation(summary = "获取指标列表", description = "获取特定患者的所有健康指标记录")
    @GetMapping("/{patientId}")
    public Result<List<HealthMetricVo>> getMetrics(@PathVariable Long patientId) {
        return Result.ok(service.findAllForPatient(patientId));
    }

    @Operation(summary = "新增健康指标", description = "为特定患者新增健康测量指标记录")
    @PostMapping("/{patientId}")
    public Result<HealthMetricVo> createMetric(
            @PathVariable Long patientId,
            @Valid @RequestBody CreateHealthMetricDto dto
    ) {
        return Result.ok(service.create(patientId, dto.getMetricType(), dto.getMetricValue()));
    }
}
