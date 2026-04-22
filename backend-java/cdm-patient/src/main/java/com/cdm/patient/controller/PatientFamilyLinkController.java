package com.cdm.patient.controller;

import com.cdm.common.domain.Result;
import com.cdm.patient.dto.CreatePatientFamilyLinkDto;
import com.cdm.patient.service.PatientFamilyLinkService;
import com.cdm.patient.vo.PatientFamilyLinkVo;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/family-links")
@Tag(name = "Family Link", description = "患者家属关系绑定")
public class PatientFamilyLinkController {

    private final PatientFamilyLinkService service;

    public PatientFamilyLinkController(PatientFamilyLinkService service) {
        this.service = service;
    }

    @Operation(summary = "查询家属绑定", description = "获取特定患者当前的家属关联列表")
    @GetMapping("/{patientId}")
    public Result<List<PatientFamilyLinkVo>> getLinks(@PathVariable Long patientId) {
        return Result.ok(service.findAllForPatient(patientId));
    }

    @Operation(summary = "绑定家属", description = "为特定患者绑定注册用户作为家属")
    @PostMapping("/{patientId}")
    public Result<PatientFamilyLinkVo> createLink(
            @PathVariable Long patientId,
            @Valid @RequestBody CreatePatientFamilyLinkDto dto
    ) {
        return Result.ok(service.linkFamily(patientId, dto.getFamilyUserId(), dto.getRelationship()));
    }
}
