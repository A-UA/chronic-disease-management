package com.cdm.patient.controller;

import com.cdm.common.domain.Result;
import com.cdm.patient.dto.CreatePatientManagerAssignmentDto;
import com.cdm.patient.service.PatientManagerAssignmentService;
import com.cdm.patient.vo.PatientManagerAssignmentVo;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/manager-assignments")
@Tag(name = "Manager Assignment", description = "患者与管理人员分配")
public class PatientManagerAssignmentController {

    private final PatientManagerAssignmentService service;

    public PatientManagerAssignmentController(PatientManagerAssignmentService service) {
        this.service = service;
    }

    @Operation(summary = "查询管理分配", description = "查询特定患者分配的管理人员及其类型")
    @GetMapping("/{patientId}")
    public Result<List<PatientManagerAssignmentVo>> getAssignments(@PathVariable String patientId) {
        return Result.ok(service.findAllForPatient(patientId));
    }

    @Operation(summary = "分配管理员", description = "为特定患者分配管家或医生")
    @PostMapping("/{patientId}")
    public Result<PatientManagerAssignmentVo> createAssignment(
            @PathVariable String patientId,
            @Valid @RequestBody CreatePatientManagerAssignmentDto dto
    ) {
        return Result.ok(service.assignManager(patientId, dto.getManagerUserId(), dto.getAssignmentType()));
    }
}
