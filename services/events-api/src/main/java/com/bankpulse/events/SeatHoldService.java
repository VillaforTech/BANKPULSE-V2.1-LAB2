package com.bankpulse.events;
import java.time.Duration;
import java.util.UUID;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.concurrent.TimeUnit;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;
@Service
public class SeatHoldService {
  private final StringRedisTemplate redis; private final Duration ttl;
  SeatHoldService(StringRedisTemplate redis,@Value("${bankpulse.events.hold-ttl-seconds:300}") long ttl){this.redis=redis;this.ttl=Duration.ofSeconds(ttl);}
  public Hold create(String eventId,String seatId,String memberId){
    String key="seat-hold:"+eventId+":"+seatId; String holdId=UUID.randomUUID().toString(); String value=holdId+"|"+memberId;
    Boolean ok=redis.opsForValue().setIfAbsent(key,value,ttl);
    if(!Boolean.TRUE.equals(ok)) throw new SeatAlreadyHeldException();
    return new Hold(holdId,eventId,seatId,memberId,ttl.toSeconds());
  }
  public void release(String eventId,String seatId,String holdId){
    String key="seat-hold:"+eventId+":"+seatId; String current=redis.opsForValue().get(key);
    if(current!=null && current.startsWith(holdId+"|")) redis.delete(key);
  }
  // Lab introspection endpoint support. KEYS is acceptable only for this small educational dataset;
  // production systems should use a bounded index/scan strategy.
  public List<ActiveHold> list(String eventId){
    Set<String> keys=redis.keys("seat-hold:"+eventId+":*"); List<ActiveHold> result=new ArrayList<>();
    if(keys==null) return result;
    for(String key:keys){
      String value=redis.opsForValue().get(key); if(value==null) continue;
      String[] parts=value.split("\\|",2); String seatId=key.substring(key.lastIndexOf(':')+1);
      Long ttl=redis.getExpire(key, TimeUnit.SECONDS);
      result.add(new ActiveHold(parts[0],eventId,seatId,parts.length>1?parts[1]:"unknown",ttl==null?0:Math.max(ttl,0)));
    }
    return result;
  }
  public record Hold(String holdId,String eventId,String seatId,String memberId,long expiresInSeconds){}
  public record ActiveHold(String holdId,String eventId,String seatId,String memberId,long expiresInSeconds){}
  public static class SeatAlreadyHeldException extends RuntimeException{}
}
