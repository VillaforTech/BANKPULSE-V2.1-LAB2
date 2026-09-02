package com.bankpulse.events;
import jakarta.persistence.*;
import java.time.Instant;
@Entity @Table(name="events")
public class EventEntity {
  @Id @GeneratedValue(strategy=GenerationType.UUID) private String id;
  private String name; private String venue; private Instant startsAt; private String status; private int seatCapacity;
  protected EventEntity(){}
  public EventEntity(String id,String name,String venue,Instant startsAt,String status,int seatCapacity){this.id=id;this.name=name;this.venue=venue;this.startsAt=startsAt;this.status=status;this.seatCapacity=seatCapacity;}
  public String getId(){return id;} public String getName(){return name;} public String getVenue(){return venue;} public Instant getStartsAt(){return startsAt;} public String getStatus(){return status;} public int getSeatCapacity(){return seatCapacity;}
}
