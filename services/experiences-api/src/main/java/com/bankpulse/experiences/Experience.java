package com.bankpulse.experiences;

import java.math.BigDecimal;
import java.time.Instant;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;

@Document("experiences")
public record Experience(@Id String id, String name, String city, String category, BigDecimal price, int capacity, boolean active, Instant createdAt) {}
