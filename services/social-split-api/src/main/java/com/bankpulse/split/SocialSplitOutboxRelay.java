package com.bankpulse.split;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaOperations;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class SocialSplitOutboxRelay {
  private static final Logger log=LoggerFactory.getLogger(SocialSplitOutboxRelay.class); private final SocialSplitOutboxRepository outbox; private final KafkaOperations<String,String> kafka; private final ObjectMapper mapper; private final String topic;
  public SocialSplitOutboxRelay(SocialSplitOutboxRepository outbox,KafkaOperations<String,String> kafka,ObjectMapper mapper,@Value("${social-split.events-topic:bankpulse.social-split.events.v1}")String topic){this.outbox=outbox;this.kafka=kafka;this.mapper=mapper;this.topic=topic;}
  @Scheduled(fixedDelayString="${social-split.outbox.poll-ms:100}") @Transactional public void publishPending(){for(SocialSplitOutboxEvent event:outbox.findTop50ByPublishedFalseOrderByOccurredAtAsc())publish(event);}
  private void publish(SocialSplitOutboxEvent event){try{kafka.send(topic,event.getAggregateId(),envelope(event)).get(900,TimeUnit.MILLISECONDS);event.markPublished();log.info("Published Social Split eventId={} aggregateId={}",event.getEventId(),event.getAggregateId());}catch(Exception ex){event.markFailed(ex.getMessage());log.warn("Social Split event remains pending eventId={} attempt={}",event.getEventId(),event.getAttempts(),ex);}}
  private String envelope(SocialSplitOutboxEvent event)throws Exception{Map<String,Object> value=new LinkedHashMap<>();value.put("eventId",event.getEventId());value.put("eventType",event.getEventType());value.put("schemaVersion",1);value.put("aggregateId",event.getAggregateId());value.put("aggregateVersion",event.getAggregateVersion());value.put("occurredAt",event.getOccurredAt().toString());value.put("payload",mapper.readTree(event.getPayload()));return mapper.writeValueAsString(value);}
}