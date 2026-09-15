package com.bankpulse.split;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.time.Instant;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.kafka.core.KafkaOperations;

class SocialSplitOutboxRelayTest {
  @SuppressWarnings("unchecked")
  @Test void retryUsesTheSameEventIdAndAggregateKey() throws Exception {
    SocialSplitOutboxRepository repository = mock(SocialSplitOutboxRepository.class);
    AtomicInteger sends = new AtomicInteger();
    List<Object[]> calls = new ArrayList<>();
    KafkaOperations<String,String> kafka = (KafkaOperations<String,String>) java.lang.reflect.Proxy.newProxyInstance(
        KafkaOperations.class.getClassLoader(), new Class[]{KafkaOperations.class}, (proxy, method, args) -> {
          if (method.getName().equals("send")) {
            calls.add(args);
            return sends.getAndIncrement() == 0
                ? CompletableFuture.failedFuture(new RuntimeException("broker"))
                : CompletableFuture.completedFuture(null);
          }
          return null;
        });
    SocialSplitOutboxEvent event = new SocialSplitOutboxEvent("event-1", "SplitCompleted", "split-1", 4, Instant.parse("2026-09-15T12:00:00Z"), "{\"closedAt\":\"2026-09-15T12:00:00Z\"}");
    when(repository.findTop50ByPublishedFalseOrderByOccurredAtAsc()).thenReturn(List.of(event));
    SocialSplitOutboxRelay relay = new SocialSplitOutboxRelay(repository, kafka, new ObjectMapper(), "topic");
    relay.publishPending();
    relay.publishPending();
    assertEquals(true, event.isPublished());
    assertEquals(1, event.getAttempts());
    assertEquals(2, calls.size());
    assertEquals("split-1", calls.get(0)[1]);
    assertEquals(calls.get(0)[2], calls.get(1)[2]);
  }
}