package com.bankpulse.experiences;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/experiences")
public class ExperienceController {
  private final ExperienceRepository repo;
  ExperienceController(ExperienceRepository repo) { this.repo = repo; }

  @GetMapping
  List<Experience> list(@RequestParam(required=false) String city) {
    return city == null ? repo.findByActiveTrue() : repo.findByCityIgnoreCaseAndActiveTrue(city);
  }

  @GetMapping("/{id}")
  Experience byId(@PathVariable String id) { return repo.findById(id).orElseThrow(); }

  @PostMapping @ResponseStatus(HttpStatus.CREATED)
  Experience create(@Valid @RequestBody CreateExperience request) {
    return repo.save(new Experience(null, request.name(), request.city(), request.category(), request.price(), request.capacity(), true, Instant.now()));
  }

  public record CreateExperience(@NotBlank String name, @NotBlank String city, @NotBlank String category,
                                 @DecimalMin("0.01") BigDecimal price, @Min(1) int capacity) {}
}
