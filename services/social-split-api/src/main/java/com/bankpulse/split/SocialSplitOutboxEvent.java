package com.bankpulse.split;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Lob;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "social_split_outbox_events")
public class SocialSplitOutboxEvent {
  @Id private String eventId;
  @Column(nullable=false) private String eventType;
  @Column(nullable=false) private String aggregateId;
  @Column(nullable=false) private long aggregateVersion;
  @Column(nullable=false) private Instant occurredAt;
  @Lob @Column(nullable=false, columnDefinition="TEXT") private String payload;
  @Column(nullable=false) private boolean published;
  @Column(nullable=false) private int attempts;
  @Column(length=500) private String lastError;
  private Instant publishedAt;
  protected SocialSplitOutboxEvent() {}
  public SocialSplitOutboxEvent(String eventId,String eventType,String aggregateId,long aggregateVersion,Instant occurredAt,String payload){this.eventId=eventId;this.eventType=eventType;this.aggregateId=aggregateId;this.aggregateVersion=aggregateVersion;this.occurredAt=occurredAt;this.payload=payload;}
  public void markPublished(){published=true;publishedAt=Instant.now();lastError=null;}
  public void markFailed(String error){attempts++;lastError=error==null?"unknown error":error.substring(0,Math.min(500,error.length()));}
  public String getEventId(){return eventId;} public String getEventType(){return eventType;} public String getAggregateId(){return aggregateId;} public long getAggregateVersion(){return aggregateVersion;} public Instant getOccurredAt(){return occurredAt;} public String getPayload(){return payload;} public boolean isPublished(){return published;} public int getAttempts(){return attempts;} public String getLastError(){return lastError;} public Instant getPublishedAt(){return publishedAt;}
}