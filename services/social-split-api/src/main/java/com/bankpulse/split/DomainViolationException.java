package com.bankpulse.split;

public class DomainViolationException extends RuntimeException {
  public DomainViolationException(String message) { super(message); }
}