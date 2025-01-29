/*
	Author: M Morano
	Date: 1/29/2025

	This is code for the microcontroller that reads the ADC. All it does is read the ADC every 250 ms, and
	transmits it to the controller when asked to. Most of it is pretty self explanatory because the SPI and
	UART interfaces are bit-banged. 
*/

#include <avr/io.h>
#include <util/delay.h>
#include <avr/interrupt.h>

#define USCK PB2
#define DO PB1
#define DI PB0
#define SS PB3
#define TRIG PB4
#define bitTime 100

volatile uint16_t timerCount = 0;	// used for setting the ADC sample rate
volatile uint8_t adcCode[4];		// 4 bytes to store the ADC value
volatile bool flag = false;        	// flag for a transmit request

ISR(PCINT0_vect) {

	// Check for falling edge
	if( ~PINB & (1 << TRIG) )
		flag = true; // set transmit flag	
}

ISR(TIMER0_COMPA_vect) {
	
    timerCount++; // increment timer every 100 us
	
}

void transmit(uint8_t outByte) {

	// send start bit
	PORTB |= (1 << DO);  
	_delay_us(bitTime); 
	PORTB &= ~(1 << DO);
	_delay_us(bitTime);

	// bit bang data
	for(uint8_t i = 0; i < 8 ; i++) {
		outByte & (1 << i) ? PORTB |= (1 << DO) : PORTB &= ~(1 << DO);
		_delay_us(bitTime);
	}

	// send stop bit and add short delay before sending next byte
	PORTB |= (1 << DO);
	_delay_us(bitTime);
	
}

// 
void readAdc() {
	
	PORTB &= ~(1 << SS); // pull SS low
	
    // loop four times to get 32 data bits from ADC
	for(uint8_t i = 0; i < 4; i++) {
		
		for(uint8_t j = 0; j < 8; j++) {
			
			(PINB & (1 << DI)) ? adcCode[i] |= (1 << (7-j)) : adcCode[i] &= ~(1 << (7-j)); // read bit from ADC
			PORTB |= (1 << USCK);   // toggle USCK to shift out next bit
			PORTB &= ~(1 << USCK);
			
		}
		
	}
	
	PORTB |= (1 << SS); // put SS high
	
}

int main(void) {

    MCUCR |= (1 << ISC01);                              // falling edge interrupt
    GIMSK |= (1 << PCIE);                               // enable pin change interrupt
    PCMSK |= (1 << TRIG);                               // enable interrupts on TRIG pin
    DDRB |= (1 << DO) | (1 << USCK) | (1 << SS);        // configure pins for output
    DDRB &= ~(1 << TRIG) | ~(1 << DI);                  // configure pins for input
    PORTB |= (1 << TRIG) | (1 << DI);                   // enable pullup resistors
	PORTB |= (1 << SS) | (1 << DO);						// idle output pins high
	PORTB &= ~(1 << USCK);								// idle USCK LOW
    TCCR0A |= (1 << WGM01);                             // configure timer0 for CTC mode
    TCCR0B |= (1 << CS01);                              // configure prescaler for div/8 = 1 MHz
    OCR0A = 99;                                         // configure for further div/100 = 10 KHz
    TIMSK |= (1 << OCIE0A);                             // enable timer0 interrupts
	sei();												// enable interrupts

    while(1) {
		
		// read adc at 4 Hz
    	if (timerCount >= 2499){

			readAdc();
			timerCount = 0; // reset timer

      	}
		
		// wait for the transmit flag to be set
		if (flag){

			// send four bytes from ADC
			for (uint8_t i = 0; i < 4; i++)
				transmit(adcCode[i]);
		
			flag = false; // clear transmit flag
			
		}
			
	}
	
}