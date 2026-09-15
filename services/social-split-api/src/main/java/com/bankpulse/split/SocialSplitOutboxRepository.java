package com.bankpulse.split;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface SocialSplitOutboxRepository extends JpaRepository<SocialSplitOutboxEvent,String>{
  List<SocialSplitOutboxEvent> findTop50ByPublishedFalseOrderByOccurredAtAsc();
}