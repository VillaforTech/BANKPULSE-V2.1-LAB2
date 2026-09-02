package com.bankpulse.events;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
@RestController @RequestMapping("/api/events")
public class EventsController {
  private final EventRepository repo; private final SeatHoldService holds;
  EventsController(EventRepository repo,SeatHoldService holds){this.repo=repo;this.holds=holds;}
  @GetMapping List<EventEntity> list(){return repo.findAll();}
  @GetMapping("/{eventId}/holds") List<SeatHoldService.ActiveHold> holds(@PathVariable String eventId){return holds.list(eventId);}
  @PostMapping("/{eventId}/holds") @ResponseStatus(HttpStatus.CREATED)
  SeatHoldService.Hold hold(@PathVariable String eventId,@Valid @RequestBody HoldRequest r){ if(!repo.existsById(eventId)) throw new IllegalArgumentException("event not found"); return holds.create(eventId,r.seatId(),r.memberId()); }
  @DeleteMapping("/{eventId}/holds/{holdId}") @ResponseStatus(HttpStatus.NO_CONTENT)
  void release(@PathVariable String eventId,@PathVariable String holdId,@RequestParam String seatId){holds.release(eventId,seatId,holdId);}
  @ExceptionHandler(SeatHoldService.SeatAlreadyHeldException.class) @ResponseStatus(HttpStatus.CONFLICT) String conflict(){return "seat already held";}
  public record HoldRequest(@NotBlank String seatId,@NotBlank String memberId){}
}
