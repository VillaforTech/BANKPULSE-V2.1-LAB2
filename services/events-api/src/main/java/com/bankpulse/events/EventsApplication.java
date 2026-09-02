package com.bankpulse.events;
import java.time.Instant;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
@SpringBootApplication
public class EventsApplication {
  public static void main(String[] args){SpringApplication.run(EventsApplication.class,args);}
  @Bean CommandLineRunner seed(EventRepository repo){return args->{if(repo.count()==0) repo.save(new EventEntity(null,"Dragon Music Night","Quito Arena",Instant.now().plusSeconds(86400*30),"PRE_SALE",12000));};}
}
