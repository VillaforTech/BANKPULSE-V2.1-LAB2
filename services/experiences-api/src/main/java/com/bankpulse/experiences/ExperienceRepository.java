package com.bankpulse.experiences;
import java.util.List;
import org.springframework.data.mongodb.repository.MongoRepository;
public interface ExperienceRepository extends MongoRepository<Experience,String> {
  List<Experience> findByActiveTrue();
  List<Experience> findByCityIgnoreCaseAndActiveTrue(String city);
}
