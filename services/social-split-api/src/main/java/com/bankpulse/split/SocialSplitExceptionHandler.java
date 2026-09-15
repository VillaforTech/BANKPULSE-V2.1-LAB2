package com.bankpulse.split;

import java.time.Instant;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@RestControllerAdvice
public class SocialSplitExceptionHandler {
  @ExceptionHandler(DomainViolationException.class)
  ResponseEntity<Map<String,Object>> domain(DomainViolationException ex) { return error(HttpStatus.UNPROCESSABLE_ENTITY, ex.getMessage()); }
  @ExceptionHandler(CompletedMutationException.class)
  ResponseEntity<Map<String,Object>> completed(CompletedMutationException ex) { return error(HttpStatus.CONFLICT, ex.getMessage()); }
  @ExceptionHandler(ResourceNotFoundException.class)
  ResponseEntity<Map<String,Object>> missing(ResourceNotFoundException ex) { return error(HttpStatus.NOT_FOUND, ex.getMessage()); }
  private ResponseEntity<Map<String,Object>> error(HttpStatus status,String message) { return ResponseEntity.status(status).body(Map.of("timestamp", Instant.now(), "status", status.value(), "error", message)); }
}