import smtplib
from email.message import EmailMessage

# --- Completa con tus datos ---
MI_GMAIL = "alejoperagallo@gmail.com"  # Tu direccion de Gmail
MI_CLAVE_16_LETRAS = "lduv jxfs agcl ulcc"  # La clave que copiaste en el Paso 1
DESTINATARIO = "alejoperagallo00@gmail.com"  # Correo de tu amigo o el tuyo para probar

# Armar el mensaje
msg = EmailMessage()
msg["Subject"] = "Prueba de envio automatico"
msg["From"] = MI_GMAIL
msg["To"] = DESTINATARIO
msg.set_content(
    "Hola! Este es un mensaje de prueba enviado desde Python para verificar la conexion."
)

print("Conectando con Gmail...")
try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(MI_GMAIL, MI_CLAVE_16_LETRAS)
        smtp.send_message(msg)
    print("¡Exito! El correo se envio correctamente.")
except Exception as e:
    print(f"Hubo un error: {e}")