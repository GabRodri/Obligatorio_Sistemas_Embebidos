#include <xc.h>

#pragma config FOSC = HS, WDTE = OFF, PWRTE = OFF, BOREN = OFF
#pragma config LVP = OFF, CPD = OFF, WRT = OFF, CP = OFF

#define _XTAL_FREQ 8000000

// Definición de pines para LEDs
#define LED_VERDE_PORT RB0
#define LED_ROJO_PORT  RB1
#define LED_VERDE_TRIS TRISB0
#define LED_ROJO_TRIS  TRISB1

#define MAX_EVENTOS 5

typedef struct {
    unsigned int tiempo;
    char cedula[9];
    unsigned char autorizado;
} Evento;

volatile unsigned int t0_overflows = 0;
volatile unsigned int segundos = 0;
volatile unsigned int ultimo_envio = 0;

Evento eventos[MAX_EVENTOS];
unsigned char num_eventos = 0;
unsigned char evento_index = 0;

void __interrupt() isr(void) {
    if (T0IF) {
        T0IF = 0;               // Limpia bandera
        t0_overflows++;         // Cuenta overflows

        if (t0_overflows >= 244) {  // 244 × 4.096 ms ? 1 segundo
            t0_overflows = 0;
            segundos++;
        }
    }
}

void timer0_init(void) {
    T0CS = 0;    // Usa reloj interno (Fosc/4)
    PSA = 0;     // Prescaler asignado a Timer0
    PS2 = 1;     // Prescaler 1:32 - bit 2
    PS1 = 0;     // Prescaler 1:32 - bit 1  
    PS0 = 0;     // Prescaler 1:32 - bit 0

    TMR0 = 0;
    T0IF = 0;
    T0IE = 1;    // Habilita interrupción de Timer0
    GIE = 1;     // Habilita interrupciones globales
}

void uart_init(void) {
    TRISC7 = 1;   // RX (pin RC7) como entrada
    TRISC6 = 0;   // TX (pin RC6) como salida
    SPBRG = 51;   // Baud rate 9600 - 8MHz
    SYNC = 0;     // Modo asíncrono
    BRGH = 1;     // High baud rate
    SPEN = 1;     // Habilitar puerto serial
    CREN = 1;     // Habilitar recepción continua
    TXEN = 1;     // Habilitar transmisión
}

void uart_write(char data) {
    while(!TXIF);  // Esperar a que el buffer de transmisión esté vacío
    TXREG = data;
}

void uart_write_string(const char *str) {
    while(*str) {
        uart_write(*str);
        str++;        
    }
}

void uint_a_string(unsigned int num, char *str, unsigned char digits) {
    char temp[10];
    unsigned char i = 0;
    unsigned char j;
    
    // Convertir número a string (invertido)
    if(num == 0) {
        temp[i++] = '0';
    } else {
        while(num > 0) {
            temp[i++] = (num % 10) + '0';
            num /= 10;
        }
    }
    
    // Rellenar con ceros a la izquierda
    while(i < digits) {
        temp[i++] = '0';
    }
    
    // Invertir el string al destino
    for(j = 0; j < i; j++) {
        str[j] = temp[i - 1 - j];
    }
    str[j] = '\0';
}

void agregar_evento(const char *cedula, unsigned char autorizado) {
    if(num_eventos < MAX_EVENTOS) {
        eventos[evento_index].tiempo = segundos;
        eventos[evento_index].autorizado = autorizado;
        
        // Copiar cédula
        unsigned char i;
        for(i = 0; i < 8 && cedula[i] != '\0'; i++) {
            eventos[evento_index].cedula[i] = cedula[i];
        }
        eventos[evento_index].cedula[i] = '\0';
        
        evento_index = (evento_index + 1) % MAX_EVENTOS;
        num_eventos++;
    }
}

void enviar_eventos_pendientes(void) {
    unsigned char i;
    char tiempo_str[5]; 
        
    for(i = 0; i < num_eventos; i++) {
        // Convertir tiempo a string con ceros a la izquierda
        uint_a_string(eventos[i].tiempo, tiempo_str, 4);
        
        // Construir y enviar el mensaje
        uart_write_string("tiempo=");
        uart_write_string(tiempo_str);
        uart_write_string(", cedula=");
        uart_write_string(eventos[i].cedula);
        uart_write_string(", autorizado=");
        uart_write_string(eventos[i].autorizado ? "Si" : "No");
        uart_write_string("\r\n");
    }
    
    // Reiniciar contador de eventos
    num_eventos = 0;
    evento_index = 0;
    
    // Reiniciar el contador de tiempo
    segundos = 0;
    ultimo_envio = segundos;
}

void verificar_envio_eventos(void) {
    // Verificar si pasaron 5 minutos (300 segundos)
    if((segundos - ultimo_envio) >= 300) {
        if(num_eventos > 0) {
            enviar_eventos_pendientes();
        } else {
            uart_write_string("No ocurrieron eventos en 5 minutos.\r\n");
            ultimo_envio = segundos;  // Actualizar el tiempo
        }
    }
    
    // Verificar si el buffer está lleno
    if(num_eventos >= MAX_EVENTOS) {
        enviar_eventos_pendientes();
    }
}

char leer_codigo_barras(void) {
    if(RCIF) {              // Si hay dato disponible
        return RCREG;       // Leer y retornar el carácter
    }
    return 0;               // No hay dato disponible
}

void eeprom_write(uint8_t addr, uint8_t data) {
    EEADR = addr;
    EEDATA = data;
    EEPGD = 0;
    WREN = 1;
    GIE = 0;
    EECON2 = 0x55;
    EECON2 = 0xAA;
    WR = 1;
    GIE = 1;
    while(WR);
    WREN = 0;
}

uint8_t eeprom_read(uint8_t addr) {
    EEADR = addr;
    EEPGD = 0;
    RD = 1;
    return EEDATA;
}

void cargar_cedula(uint8_t numero_cedula, const char *cedula) {
    uint8_t direccion_base = (numero_cedula - 1) * 8;
    for(uint8_t i = 0; i < 8; i++) {
        eeprom_write(direccion_base + i, cedula[i]);
    }
}

uint8_t comparar_con_cedulas(const char *codigo_leido) {
    char cedula_actual[9];  // 8 dígitos + null terminator
   
    // Comparar con las 5 cédulas almacenadas
    for(uint8_t i = 0; i < 5; i++) {
        uint8_t direccion_base = i * 8;
       
        // Leer cédula de la EEPROM
        for(uint8_t j = 0; j < 8; j++) {
            cedula_actual[j] = eeprom_read(direccion_base + j);
        }
        cedula_actual[8] = '\0';  // Null terminator
       
        // Comparar strings
        uint8_t iguales = 1;
        for(uint8_t k = 0; k < 8; k++) {
            if(codigo_leido[k] != cedula_actual[k]) {
                iguales = 0;
                break;
            }
        }
        if(iguales) {
            return 1;  // Encontrada
        }
    }
    return 0;  // No encontrada
}

void controlar_leds(uint8_t autorizado) {
    if(autorizado) {
        LED_VERDE_PORT = 1;  // Encender LED verde
        __delay_ms(500);
        LED_VERDE_PORT = 0;   // Apagar LED verde
    } else {
        LED_ROJO_PORT = 1;  // Encender LED rojo
        __delay_ms(500);
        LED_ROJO_PORT = 0;   // Apagar LED rojo
    }
}

void main(void) {
    char codigo_leido[20];  // Buffer para almacenar el código leído
    uint8_t index = 0;      // Índice del buffer
    char caracter = 0;      // Carácter leído
   
    // Configurar pines de LEDs como salidas
    LED_VERDE_TRIS = 0;
    LED_ROJO_TRIS = 0;
   
    // Apagar ambos LEDs inicialmente
    LED_VERDE_PORT = 0;
    LED_ROJO_PORT = 0;
   
    uart_init();            // Inicializar UART
    timer0_init();          // Inicializar Timer0
   
    if(eeprom_read(0x00) == 0xFF){  
        cargar_cedula(1, "49432642");
        cargar_cedula(2, "55787807");
        cargar_cedula(3, "50329945");
        cargar_cedula(4, "49852969");
        cargar_cedula(5, "49374418");
    }
   
    while(1) {
        // Verificar condiciones para enviar eventos
        verificar_envio_eventos();
        caracter = leer_codigo_barras();
       
        if(caracter != 0) {
            if(caracter == '\r' || caracter == '\n') {            
                codigo_leido[index] = '\0';
               
                // Verificar si es exactamente 8 caracteres
                if(index == 8) {
                    uint8_t autorizado = comparar_con_cedulas(codigo_leido);
                    
                    // Agregar evento al buffer
                    agregar_evento(codigo_leido, autorizado);
                    
                    controlar_leds(autorizado);  // Controlar LEDs según resultado
                    
                } else {
                    codigo_leido[7]='@';
                    // Agregar evento al buffer (incluso si falla)
                    agregar_evento(codigo_leido, 0);
                    
                    controlar_leds(0);  // Longitud incorrecta = No autorizado
                }
                index = 0;                  
                caracter = 0;
               
            } else if(index <= 8) {
                codigo_leido[index] = caracter;  // Almacenar carácter en buffer
                index++;
            }
        }
    }
}