package com.cdm.patient.controller;

import com.cdm.common.security.IdentityPayload;
import com.cdm.patient.entity.PatientProfileEntity;
import com.cdm.patient.service.PatientService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.web.bind.annotation.*;
import java.util.Base64;
import java.util.List;

@RestController
@RequestMapping("/api/v1/patients")
public class PatientController {

    private final PatientService service;

    public PatientController(PatientService service) {
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

    @GetMapping
    public List<PatientProfileEntity> getPatients(
            @RequestHeader("X-Identity-Base64") String identityHeader
    ) {
        IdentityPayload identity = getIdentity(identityHeader);
        return service.findAll(identity);
    }

    @PostMapping
    public PatientProfileEntity createPatient(
            @RequestHeader("X-Identity-Base64") String identityHeader,
            @RequestParam String name,
            @RequestParam String gender
    ) {
        IdentityPayload identity = getIdentity(identityHeader);
        return service.createPatient(identity, name, gender);
    }
}
