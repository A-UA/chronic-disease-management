package com.cdm.patient.controller;

import com.cdm.common.security.IdentityPayload;
import com.cdm.patient.entity.HealthMetricEntity;
import com.cdm.patient.service.HealthMetricService;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.web.bind.annotation.*;
import java.util.Base64;
import java.util.List;

@RestController
@RequestMapping("/api/v1/health-metrics")
public class HealthMetricController {

    private final HealthMetricService service;

    public HealthMetricController(HealthMetricService service) {
        this.service = service;
    }

    // A basic stub for resolving identity from header
    private IdentityPayload getIdentity(String base64Identity) {
        try {
            String json = new String(Base64.getDecoder().decode(base64Identity));
            return new ObjectMapper().readValue(json, IdentityPayload.class);
        } catch (Exception e) {
            throw new RuntimeException("Invalid identity header", e);
        }
    }

    @GetMapping("/{patientId}")
    public List<HealthMetricEntity> getMetrics(
            @RequestHeader("X-Identity-Base64") String identityHeader,
            @PathVariable Long patientId
    ) {
        IdentityPayload identity = getIdentity(identityHeader);
        return service.findAllForPatient(identity, patientId);
    }

    @PostMapping("/{patientId}")
    public HealthMetricEntity createMetric(
            @RequestHeader("X-Identity-Base64") String identityHeader,
            @PathVariable Long patientId,
            @RequestParam String metricType,
            @RequestParam String metricValue
    ) {
        IdentityPayload identity = getIdentity(identityHeader);
        return service.create(identity, patientId, metricType, metricValue);
    }
}
