package com.bankpulse.split;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.transaction.Transactional;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

@Service
public class SocialSplitService {
  private final SplitSessionRepository sessions; private final SocialSplitOutboxRepository outbox; private final SocialSplitOutboxRelay relay; private final ObjectMapper mapper;
  public SocialSplitService(SplitSessionRepository sessions,SocialSplitOutboxRepository outbox,SocialSplitOutboxRelay relay,ObjectMapper mapper){this.sessions=sessions;this.outbox=outbox;this.relay=relay;this.mapper=mapper;}
  @Transactional public SplitSession create(String hostMemberId,BigDecimal totalAmount,String currency){SplitSession session=sessions.save(new SplitSession(hostMemberId,totalAmount,currency));session.advanceVersion();outbox.save(event(session,"SplitCreated",Map.of("sessionId",session.getId(),"createdAt",session.getCreatedAt(),"totalAmount",session.getTotalAmount(),"currency",session.getCurrency())));return afterCommit(session);}
  @Transactional public SplitSession addParticipant(String id,String memberId,BigDecimal share){SplitSession session=get(id);session.addParticipant(memberId,share);session.advanceVersion();sessions.save(session);SplitParticipant p=session.getParticipants().get(session.getParticipants().size()-1);outbox.save(event(session,"ParticipantAdded",Map.of("participantId",p.getId(),"memberId",p.getMemberId(),"shareAmount",p.getShareAmount())));return afterCommit(session);}
  @Transactional public SplitSession authorize(String id,String participantId,String paymentReference){SplitSession session=get(id);session.authorize(participantId,paymentReference);session.advanceVersion();sessions.save(session);outbox.save(event(session,"ParticipantAuthorized",Map.of("participantId",participantId,"paymentReference","present")));return afterCommit(session);}
  @Transactional public SplitSession close(String id){SplitSession session=get(id);if(!session.closeIfAuthorized())return session;session.advanceVersion();sessions.save(session);outbox.save(event(session,"SplitCompleted",Map.of("closedAt",session.getClosedAt())));return afterCommit(session);}
  @Transactional public SplitSession get(String id){return sessions.findById(id).orElseThrow(()->new ResourceNotFoundException("split session not found"));}
  private SocialSplitOutboxEvent event(SplitSession session,String type,Map<String,Object> payload){Instant occurredAt=Instant.now();Map<String,Object> envelope=new LinkedHashMap<>();String eventId=UUID.randomUUID().toString();envelope.put("eventId",eventId);envelope.put("eventType",type);envelope.put("schemaVersion",1);envelope.put("aggregateId",session.getId());envelope.put("aggregateVersion",session.getAggregateVersion());envelope.put("occurredAt",occurredAt);envelope.put("payload",payload);try{return new SocialSplitOutboxEvent(eventId,type,session.getId(),session.getAggregateVersion(),occurredAt,mapper.writeValueAsString(payload));}catch(JsonProcessingException ex){throw new IllegalStateException("cannot serialize social split event",ex);}}
  private SplitSession afterCommit(SplitSession session){if(TransactionSynchronizationManager.isSynchronizationActive()){TransactionSynchronizationManager.registerSynchronization(new TransactionSynchronization(){@Override public void afterCommit(){relay.publishPending();}});}return session;}
}