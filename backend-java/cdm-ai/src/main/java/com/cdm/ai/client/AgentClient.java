package com.cdm.ai.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestPart;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.multipart.MultipartFile;

import java.util.Map;

@FeignClient(name = "agentClient", url = "${agent.url}")
public interface AgentClient {

    @PostMapping(value = "/internal/knowledge/parse", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    Map<String, Object> parseDocument(@RequestPart("file") MultipartFile file, @RequestParam("kb_id") String kbId);

}
