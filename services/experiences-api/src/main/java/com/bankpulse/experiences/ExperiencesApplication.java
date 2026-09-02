package com.bankpulse.experiences;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class ExperiencesApplication {
  public static void main(String[] args) { SpringApplication.run(ExperiencesApplication.class, args); }

  @Bean CommandLineRunner seed(ExperienceRepository repo) {
    return args -> {
      if (repo.count() == 0) {
        repo.saveAll(List.of(
          new Experience(null, "Casa Dragon Signature Dinner", "Quito", "GASTRONOMY", new BigDecimal("65.00"), 24, true, Instant.now()),
          new Experience(null, "Andean Chef Table", "Cumbaya", "GASTRONOMY", new BigDecimal("85.00"), 12, true, Instant.now())
        ));
      }
    };
  }
}
