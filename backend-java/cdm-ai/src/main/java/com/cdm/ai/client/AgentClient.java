package com.cdm.ai.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@FeignClient(name = "agentClient", url = "${agent.url:http://localhost:8000}")
public interface AgentClient {

    @PostMapping(value = "/internal/knowledge/parse", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    Map<String, Object> parseDocument(@RequestPart("file") MultipartFile file, @RequestParam("kb_id") String kbId);

    @org.springframework.web.bind.annotation.DeleteMapping("/internal/knowledge/vectors/kb/{kbId}")
    void deleteKbVectors(@org.springframework.web.bind.annotation.PathVariable("kbId") String kbId);

    @org.springframework.web.bind.annotation.DeleteMapping("/internal/knowledge/vectors/kb/{kbId}/doc/{filename}")
    void deleteDocVectors(@org.springframework.web.bind.annotation.PathVariable("kbId") String kbId, @org.springframework.web.bind.annotation.PathVariable("filename") String filename);
}
