package com.cdm.auth;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class AuthApplication {
    public static void main(String[] args) {
        System.out.println("Starting Auth Service...");
        SpringApplication.run(AuthApplication.class, args);
    }
}
