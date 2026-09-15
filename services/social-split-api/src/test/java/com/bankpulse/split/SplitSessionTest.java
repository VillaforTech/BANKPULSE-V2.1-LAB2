package com.bankpulse.split;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import java.math.BigDecimal;
import org.junit.jupiter.api.Test;

class SplitSessionTest {
  @Test void closesWhenAuthorizedSharesEqualTotal() {
    SplitSession session = session("100");
    session.addParticipant("member-1", new BigDecimal("60"));
    session.addParticipant("member-2", new BigDecimal("40"));
    session.getParticipants().get(0).authorize("pay-1");
    session.getParticipants().get(1).authorize("pay-2");
    assertEquals(true, session.closeIfAuthorized());
    assertEquals("COMPLETED", session.getStatus());
  }

  @Test void rejectsShareShortfallAndExcess() {
    for (String secondShare : new String[]{"30", "50"}) {
      SplitSession session = session("100");
      session.addParticipant("member-1", new BigDecimal("60"));
      session.addParticipant("member-2", new BigDecimal(secondShare));
      session.getParticipants().get(0).authorize("pay-1");
      session.getParticipants().get(1).authorize("pay-2");
      assertThrows(DomainViolationException.class, session::closeIfAuthorized);
      assertEquals("OPEN", session.getStatus());
    }
  }

  @Test void rejectsEmptyUnauthorizedAndMissingParticipants() {
    assertThrows(DomainViolationException.class, () -> session("100").closeIfAuthorized());
    SplitSession unauthorized = session("100");
    unauthorized.addParticipant("member-1", new BigDecimal("100"));
    assertThrows(DomainViolationException.class, unauthorized::closeIfAuthorized);
  }

  @Test void repeatedCloseIsIdempotentAndCompletedMutationIsRejected() {
    SplitSession session = session("100");
    session.addParticipant("member-1", new BigDecimal("100"));
    session.getParticipants().get(0).authorize("pay-1");
    assertEquals(true, session.closeIfAuthorized());
    var closedAt = session.getClosedAt();
    assertEquals(false, session.closeIfAuthorized());
    assertEquals(closedAt, session.getClosedAt());
    assertThrows(CompletedMutationException.class, () -> session.addParticipant("member-2", new BigDecimal("1")));
  }

  private SplitSession session(String total) { return new SplitSession("host", new BigDecimal(total), "USD"); }
}