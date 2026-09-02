package com.bankpulse.split;
import jakarta.transaction.Transactional;
import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/splits")
public class SocialSplitController {
  private final SplitSessionRepository repo;
  SocialSplitController(SplitSessionRepository repo){this.repo=repo;}
  @PostMapping @ResponseStatus(HttpStatus.CREATED)
  SplitSession create(@Valid @RequestBody CreateSplit r){return repo.save(new SplitSession(r.hostMemberId(),r.totalAmount(),r.currency()));}
  @GetMapping("/{id}") SplitSession get(@PathVariable String id){return repo.findById(id).orElseThrow();}
  @PostMapping("/{id}/participants") @Transactional
  SplitSession participant(@PathVariable String id,@Valid @RequestBody AddParticipant r){SplitSession s=get(id);s.addParticipant(r.memberId(),r.shareAmount());return repo.save(s);}
  @PostMapping("/{id}/participants/{participantId}/authorize") @Transactional
  SplitSession authorize(@PathVariable String id,@PathVariable String participantId,@Valid @RequestBody Authorize r){SplitSession s=get(id);SplitParticipant p=s.getParticipants().stream().filter(x->x.getId().equals(participantId)).findFirst().orElseThrow();p.authorize(r.paymentReference());return repo.save(s);}
  @PostMapping("/{id}/close") @Transactional
  SplitSession close(@PathVariable String id){SplitSession s=get(id);s.closeIfAuthorized();return repo.save(s);}
  public record CreateSplit(@NotBlank String hostMemberId,@DecimalMin("0.01") BigDecimal totalAmount,@Pattern(regexp="[A-Z]{3}") String currency){}
  public record AddParticipant(@NotBlank String memberId,@DecimalMin("0.01") BigDecimal shareAmount){}
  public record Authorize(@NotBlank String paymentReference){}
}
