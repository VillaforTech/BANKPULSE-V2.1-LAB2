package com.bankpulse.split;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
@Entity @Table(name="split_sessions")
public class SplitSession {
  @Id @GeneratedValue(strategy=GenerationType.UUID) private String id;
  private String hostMemberId; private BigDecimal totalAmount; private String currency; private String status; private Instant createdAt; private Instant closedAt;
  @Column(nullable=false) private long aggregateVersion;
  @OneToMany(mappedBy="session",cascade=CascadeType.ALL,orphanRemoval=true,fetch=FetchType.EAGER) private List<SplitParticipant> participants=new ArrayList<>();
  protected SplitSession(){}
  public SplitSession(String hostMemberId,BigDecimal totalAmount,String currency){this.hostMemberId=hostMemberId;this.totalAmount=totalAmount;this.currency=currency;this.status="OPEN";this.createdAt=Instant.now();}
  public String getId(){return id;} public String getHostMemberId(){return hostMemberId;} public BigDecimal getTotalAmount(){return totalAmount;} public String getCurrency(){return currency;} public String getStatus(){return status;} public Instant getCreatedAt(){return createdAt;} public Instant getClosedAt(){return closedAt;} public long getAggregateVersion(){return aggregateVersion;} public List<SplitParticipant> getParticipants(){return participants;}
  public void advanceVersion(){aggregateVersion++;}
  public void addParticipant(String memberId,BigDecimal share){ensureOpen();participants.add(new SplitParticipant(this,memberId,share));}
  public void authorize(String participantId,String paymentReference){ensureOpen(); SplitParticipant participant=participants.stream().filter(p->p.getId().equals(participantId)).findFirst().orElseThrow(()->new ResourceNotFoundException("participant not found")); participant.authorize(paymentReference);}
  public boolean closeIfAuthorized(){
    if("COMPLETED".equals(status)) return false;
    if(participants.isEmpty()) throw new DomainViolationException("at least one participant is required");
    if(participants.stream().anyMatch(p->p.getShareAmount()==null||p.getShareAmount().signum()<=0)) throw new DomainViolationException("all shares must be positive");
    BigDecimal shares=participants.stream().map(SplitParticipant::getShareAmount).reduce(BigDecimal.ZERO,BigDecimal::add);
    if(shares.compareTo(totalAmount)!=0) throw new DomainViolationException("participant shares must equal total amount");
    if(participants.stream().anyMatch(p->!p.isAuthorized())) throw new DomainViolationException("all participants must authorize");
    if(participants.stream().anyMatch(p->p.getPaymentReference()==null||p.getPaymentReference().isBlank())) throw new DomainViolationException("all authorized participants need a payment reference");
    status="COMPLETED"; closedAt=Instant.now(); return true;
  }
  private void ensureOpen(){if("COMPLETED".equals(status)) throw new CompletedMutationException("completed sessions cannot be changed");}
}
