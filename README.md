# AI Finance Orchestrator


## 📄 Descripción general

Este repositorio contiene la documentación del **prototipo funcional de un agente de Inteligencia Artificial** que automatiza el proceso de facturación empresarial en AWS.

El sistema recibe correos electrónicos con archivos Excel adjuntos, interpreta los datos de facturación mediante un agente de IA (Claude en Amazon Bedrock), genera cuentas de cobro en formato PDF y envía correos corporativos programados al cliente.

El objetivo principal de esta documentación es **servir como guía técnica paso a paso para el equipo de desarrollo**, definiendo claramente el flujo del sistema y las responsabilidades de cada rol.

---

## 🎯 Objetivo del prototipo

- Automatizar el proceso de facturación empresarial.
- Reducir intervención manual en la interpretación de archivos Excel.
- Estandarizar la generación de cuentas de cobro en PDF.
- Programar y enviar correos corporativos de forma automática.
- Demostrar el uso de IA en un flujo real de negocio sobre AWS.

---

## 🧩 Alcance del sistema

El prototipo incluye:

- Recepción de correos electrónicos mediante Amazon SES.
- Almacenamiento de correos, archivos Excel y PDFs en Amazon S3.
- Procesamiento del flujo mediante AWS Lambda.
- Interpretación inteligente de datos usando Amazon Bedrock (Claude).
- Generación de cuentas de cobro en PDF.
- Programación y envío de correos usando EventBridge y SES.
- Registro y auditoría del proceso en DynamoDB.

---

## 🔄 Flujo general del sistema

1. Llega un correo electrónico con un archivo Excel adjunto.
2. Amazon SES almacena el correo en un bucket S3.
3. Una Lambda procesa el correo y extrae el archivo Excel.
4. El Excel es interpretado por un agente de IA.
5. Se valida la información de facturación.
6. Se genera una cuenta de cobro en PDF.
7. Se programa el envío del correo al cliente.
8. El sistema registra el estado del proceso.

---

## ✅ Resultado esperado

Al finalizar la implementación del prototipo, el sistema debe ser capaz de:

- Procesar automáticamente correos con archivos Excel.
- Interpretar datos de facturación aunque las columnas cambien.
- Generar cuentas de cobro profesionales en PDF.
- Enviar correos corporativos programados al cliente.
- Mantener trazabilidad completa del proceso.

