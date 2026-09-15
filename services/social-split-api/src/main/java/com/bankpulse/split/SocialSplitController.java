package com.bankpulse.split;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/splits")
public class SocialSplitController {
  private final SocialSplitService service;
  SocialSplitController(SocialSplitService service){this.service=service;}
  @PostMapping @ResponseStatus(HttpStatus.CREATED)
  SplitSession create(@Valid @RequestBody CreateSplit r){return service.create(r.hostMemberId(),r.totalAmount(),r.currency());}
  @GetMapping("/{id}") SplitSession get(@PathVariable String id){return service.get(id);}
  @PostMapping("/{id}/participants") SplitSession participant(@PathVariable String id,@Valid @RequestBody AddParticipant r){return service.addParticipant(id,r.memberId(),r.shareAmount());}
  @PostMapping("/{id}/participants/{participantId}/authorize") SplitSession authorize(@PathVariable String id,@PathVariable String participantId,@Valid @RequestBody Authorize r){return service.authorize(id,participantId,r.paymentReference());}
  @PostMapping("/{id}/close") SplitSession close(@PathVariable String id){return service.close(id);}
  public record CreateSplit(@NotBlank String hostMemberId,@DecimalMin("0.01") BigDecimal totalAmount,@Pattern(regexp="[A-Z]{3}") String currency){}
  public record AddParticipant(@NotBlank String memberId,@DecimalMin("0.01") BigDecimal shareAmount){}
  public record Authorize(@NotBlank String paymentReference){}
}
