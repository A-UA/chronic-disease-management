package com.cdm.patient.controller;

import com.cdm.common.security.IdentityPayload;
import com.cdm.patient.entity.ManagementSuggestionEntity;
import com.cdm.patient.service.ManagementSuggestionService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.web.bind.annotation.*;
import java.util.Base64;
import java.util.List;

@RestController
@RequestMapping("/api/v1/management-suggestions")
public class ManagementSuggestionController {

    private final ManagementSuggestionService service;

    public ManagementSuggestionController(ManagementSuggestionService service) {
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
    public List<ManagementSuggestionEntity> getSuggestions(
            @RequestHeader("X-Identity-Base64") String identityHeader,
            @PathVariable Long patientId
    ) {
        IdentityPayload identity = getIdentity(identityHeader);
        return service.findAllForPatient(identity, patientId);
    }

    @PostMapping("/{patientId}")
    public ManagementSuggestionEntity createSuggestion(
            @RequestHeader("X-Identity-Base64") String identityHeader,
            @PathVariable Long patientId,
            @RequestParam String suggestionType,
            @RequestParam String content
    ) {
        IdentityPayload identity = getIdentity(identityHeader);
        return service.createSuggestion(identity, patientId, suggestionType, content);
    }
}
