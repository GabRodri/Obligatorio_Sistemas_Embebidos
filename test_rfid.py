from mfrc522 import SimpleMFRC522
import RPi.GPIO as GPIO

reader = SimpleMFRC522()

try:
    print("Acerca la tarjeta al lector...")
    id, text = reader.read()
    print(f"ID: {id}")
    print(f"Texto: {text}")
finally:
    GPIO.cleanup()

