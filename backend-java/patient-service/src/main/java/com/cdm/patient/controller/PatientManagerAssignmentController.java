package com.cdm.patient.controller;

import com.cdm.common.security.IdentityPayload;
import com.cdm.patient.entity.PatientManagerAssignmentEntity;
import com.cdm.patient.service.PatientManagerAssignmentService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.web.bind.annotation.*;
import java.util.Base64;
import java.util.List;

@RestController
@RequestMapping("/api/v1/manager-assignments")
public class PatientManagerAssignmentController {

    private final PatientManagerAssignmentService service;

    public PatientManagerAssignmentController(PatientManagerAssignmentService service) {
        this.service = service;
    }

    private IdentityPayload getIdentity(String base64Identity) {
        try {
            String json = new String(Base64.getDecoder().decode(base64Identity));
            return new ObjectMapper().readValue(json, IdentityPayload.class);
        } catch (Exception e) {
            throw new RuntimeException("Invalid identity header", e);
        }
    }

    @GetMapping("/{patientId}")
    public List<PatientManagerAssignmentEntity> getAssignments(
            @RequestHeader("X-Identity-Base64") String identityHeader,
            @PathVariable Long patientId
    ) {
        IdentityPayload identity = getIdentity(identityHeader);
        return service.findAllForPatient(identity, patientId);
    }

    @PostMapping("/{patientId}")
    public PatientManagerAssignmentEntity createAssignment(
            @RequestHeader("X-Identity-Base64") String identityHeader,
            @PathVariable Long patientId,
            @RequestParam Long managerUserId,
            @RequestParam String assignmentType
    ) {
        IdentityPayload identity = getIdentity(identityHeader);
        return service.assignManager(identity, patientId, managerUserId, assignmentType);
    }
}
