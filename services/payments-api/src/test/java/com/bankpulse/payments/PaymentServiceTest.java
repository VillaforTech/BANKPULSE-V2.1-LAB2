package com.bankpulse.payments;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.Test;

class PaymentServiceTest {
    @Test void retryReturnsPersistedIdentityWithoutCreatingAnotherEvent() {
        var payments = mock(PaymentRepository.class);
        var outbox = mock(OutboxRepository.class);
        var saved = new Payment("existing", "key", "EC-4242", new BigDecimal("27.50"), "USD", "ACCEPTED", Instant.parse("2026-09-15T12:00:00.123Z"));
        when(payments.findByIdempotencyKey("key")).thenReturn(Optional.of(saved));
        var service = new PaymentService(payments, outbox, new ObjectMapper());
        assertSame(saved, service.create("key", new PaymentController.PaymentRequest("EC-4242", new BigDecimal("27.50"), "USD")));
        verify(payments, never()).save(any());
        verifyNoInteractions(outbox);
    }
    @Test void firstResponseAndEventUseDatabaseRepresentableValues() throws Exception {
        var payments = mock(PaymentRepository.class);
        var outbox = mock(OutboxRepository.class);
        when(payments.findByIdempotencyKey("new-key")).thenReturn(Optional.empty());
        var mapper = new ObjectMapper().registerModule(new JavaTimeModule());
        var service = new PaymentService(payments, outbox, mapper);
        var payment = service.create("new-key", new PaymentController.PaymentRequest("EC-4242", new BigDecimal("27.5"), "usd"));
        assertEquals(new BigDecimal("27.50"), payment.getAmount());
        assertEquals("USD", payment.getCurrency());
        assertEquals(0, payment.getCreatedAt().getNano() % 1_000_000);
        verify(payments).save(payment);
        verify(outbox).save(any(OutboxEvent.class));
    }
}
