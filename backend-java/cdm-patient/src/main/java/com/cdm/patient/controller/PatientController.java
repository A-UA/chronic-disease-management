package com.cdm.patient.controller;

import com.cdm.common.domain.Result;
import com.cdm.patient.dto.CreatePatientDto;
import com.cdm.patient.service.PatientService;
import com.cdm.patient.vo.PatientVo;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/patients")
@Tag(name = "Patient", description = "患者基本信息管理")
public class PatientController {

    private final PatientService service;

    public PatientController(PatientService service) {
        this.service = service;
    }

    @Operation(summary = "患者列表", description = "获取当前组织下所有的患者档案")
    @GetMapping
    public Result<List<PatientVo>> getPatients() {
        return Result.ok(service.findAll());
    }

    @Operation(summary = "新建患者", description = "创建一条新的患者档案")
    @PostMapping
    public Result<PatientVo> createPatient(@Valid @RequestBody CreatePatientDto dto) {
        return Result.ok(service.createPatient(dto.getName(), dto.getGender()));
    }
}
