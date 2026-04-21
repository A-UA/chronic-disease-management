package com.cdm.auth.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

@Getter
public class BusinessException extends RuntimeException {
    private final HttpStatus status;
    private final String code;

    public BusinessException(HttpStatus status, String code, String message) {
        super(message);
        this.status = status;
        this.code = code;
    }

    public static BusinessException notFound(String msg) {
        return new BusinessException(HttpStatus.NOT_FOUND, "NOT_FOUND", msg);
    }

    public static BusinessException forbidden(String msg) {
        return new BusinessException(HttpStatus.FORBIDDEN, "FORBIDDEN", msg);
    }

    public static BusinessException validation(String msg) {
        return new BusinessException(HttpStatus.UNPROCESSABLE_ENTITY, "VALIDATION_ERROR", msg);
    }
}
