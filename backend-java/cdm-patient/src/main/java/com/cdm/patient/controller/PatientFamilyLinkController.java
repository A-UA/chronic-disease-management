package com.cdm.patient.controller;

import com.cdm.common.security.IdentityPayload;
import com.cdm.patient.entity.PatientFamilyLinkEntity;
import com.cdm.patient.service.PatientFamilyLinkService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.web.bind.annotation.*;
import java.util.Base64;
import java.util.List;

@RestController
@RequestMapping("/api/v1/family-links")
public class PatientFamilyLinkController {

    private final PatientFamilyLinkService service;

    public PatientFamilyLinkController(PatientFamilyLinkService service) {
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
    public List<PatientFamilyLinkEntity> getLinks(
            @RequestHeader("X-Identity-Base64") String identityHeader,
            @PathVariable Long patientId
    ) {
        IdentityPayload identity = getIdentity(identityHeader);
        return service.findAllForPatient(identity, patientId);
    }

    @PostMapping("/{patientId}")
    public PatientFamilyLinkEntity createLink(
            @RequestHeader("X-Identity-Base64") String identityHeader,
            @PathVariable Long patientId,
            @RequestParam Long familyUserId,
            @RequestParam String relationship
    ) {
        IdentityPayload identity = getIdentity(identityHeader);
        return service.linkFamily(identity, patientId, familyUserId, relationship);
    }
}
