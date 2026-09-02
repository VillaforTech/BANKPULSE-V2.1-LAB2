package com.bankpulse.travel;
import java.util.List;
import org.springframework.data.mongodb.repository.MongoRepository;
public interface RedemptionRepository extends MongoRepository<Redemption,String>{ List<Redemption> findByMemberId(String memberId); }
