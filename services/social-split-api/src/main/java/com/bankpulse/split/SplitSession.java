package com.bankpulse.split;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
@Entity @Table(name="split_sessions")
public class SplitSession {
  @Id @GeneratedValue(strategy=GenerationType.UUID) private String id;
  private String hostMemberId; private BigDecimal totalAmount; private String currency; private String status; private Instant createdAt;
  @OneToMany(mappedBy="session",cascade=CascadeType.ALL,orphanRemoval=true,fetch=FetchType.EAGER) private List<SplitParticipant> participants=new ArrayList<>();
  protected SplitSession(){}
  public SplitSession(String hostMemberId,BigDecimal totalAmount,String currency){this.hostMemberId=hostMemberId;this.totalAmount=totalAmount;this.currency=currency;this.status="OPEN";this.createdAt=Instant.now();}
  public String getId(){return id;} public String getHostMemberId(){return hostMemberId;} public BigDecimal getTotalAmount(){return totalAmount;} public String getCurrency(){return currency;} public String getStatus(){return status;} public Instant getCreatedAt(){return createdAt;} public List<SplitParticipant> getParticipants(){return participants;}
  public void addParticipant(String memberId,BigDecimal share){participants.add(new SplitParticipant(this,memberId,share));}
  public void closeIfAuthorized(){ if(participants.isEmpty()||participants.stream().anyMatch(p->!p.isAuthorized())) throw new IllegalStateException("all participants must authorize"); status="COMPLETED"; }
}
