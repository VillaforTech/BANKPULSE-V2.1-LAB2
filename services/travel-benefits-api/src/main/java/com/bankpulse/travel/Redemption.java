package com.bankpulse.travel;
import java.time.Instant;
import org.springframework.data.annotation.Id;
import org.springframework.data.mongodb.core.mapping.Document;
@Document("travel_redemptions")
public record Redemption(@Id String id, String memberId, String benefitCode, String status, Instant usedAt, Instant synchronizedAt) {}
