package com.bankpulse.split;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class SocialSplitServiceTest {
  @Test void rejectedCloseDoesNotCreateAnOutboxEvent() {
    SplitSessionRepository sessions = mock(SplitSessionRepository.class);
    SocialSplitOutboxRepository outbox = mock(SocialSplitOutboxRepository.class);
    SplitSession session = new SplitSession("host", new BigDecimal("100"), "USD");
    session.addParticipant("member", new BigDecimal("90"));
    when(sessions.findById("split-1")).thenReturn(java.util.Optional.of(session));
    SocialSplitService service = new SocialSplitService(sessions, outbox, null, new ObjectMapper());

    assertThrows(DomainViolationException.class, () -> service.close("split-1"));
    verify(outbox, org.mockito.Mockito.never()).save(org.mockito.ArgumentMatchers.any());
  }
}