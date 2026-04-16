package com.cdm.patient.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;
import java.util.Map;

@Component
public class AgentClient {
    private final RestTemplate restTemplate;

    @Value("${agent.url}")
    private String agentUrl;

    public AgentClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public int parseDocument(MultipartFile file, Long kbId) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", file.getResource());
        body.add("kb_id", kbId.toString());

        HttpEntity<MultiValueMap<String, Object>> requestEntity = new HttpEntity<>(body, headers);
        
        try {
            ResponseEntity<Map> response = restTemplate.postForEntity(
                agentUrl + "/internal/knowledge/parse", 
                requestEntity, 
                Map.class
            );
            if(response.getStatusCode().is2xxSuccessful() && response.getBody() != null) {
                return (Integer) response.getBody().getOrDefault("chunk_count", 0);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return 0;
    }
}
