package com.bankpulse.split;
import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.*;
import java.math.BigDecimal;
@Entity @Table(name="split_participants")
public class SplitParticipant {
  @Id @GeneratedValue(strategy=GenerationType.UUID) private String id;
  @ManyToOne(fetch=FetchType.LAZY) @JoinColumn(name="session_id") @JsonIgnore private SplitSession session;
  private String memberId; private BigDecimal shareAmount; private boolean authorized; private String paymentReference;
  protected SplitParticipant(){}
  SplitParticipant(SplitSession session,String memberId,BigDecimal shareAmount){this.session=session;this.memberId=memberId;this.shareAmount=shareAmount;}
  public String getId(){return id;} public String getMemberId(){return memberId;} public BigDecimal getShareAmount(){return shareAmount;} public boolean isAuthorized(){return authorized;} public String getPaymentReference(){return paymentReference;}
  public void authorize(String paymentReference){this.authorized=true;this.paymentReference=paymentReference;}
}
