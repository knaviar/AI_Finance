# AI Finance Orchestrator

> Pipeline serverless que recibe emails con facturas Excel, genera cuentas de cobro mediante IA y las envía automáticamente por correo.
> 
## 📄 Descripción general

Este repositorio contiene la documentación del **prototipo funcional de un agente de Inteligencia Artificial** que automatiza el proceso de facturación empresarial en AWS.

El sistema recibe correos electrónicos con archivos Excel adjuntos, interpreta los datos de facturación mediante un agente de IA (Claude en Amazon Bedrock), genera cuentas de cobro en formato PDF y envía correos corporativos programados al cliente.

El objetivo principal de esta documentación es **servir como guía técnica paso a paso para el equipo de desarrollo**, definiendo claramente el flujo del sistema y las responsabilidades de cada rol.



## Tabla de contenidos

- [Arquitectura](#arquitectura)
- [Componentes](#componentes)
- [Recursos AWS](#recursos-aws)
- [Variables de entorno](#variables-de-entorno)


---

## Arquitectura

```
Email entrante
    │
    ▼
SES recibe → S3: incoming/
    │
    ▼
Lambda 1 — facturacion-trigger
    • Filtra por asunto "CUENTA DE COBRO"
    • Extrae Excel adjunto
    │
    ▼ S3: processed/
    │
Lambda 2 — facturacion-orquestador
    • Lee Excel, agrupa por Nro documento
    • Llama Amazon Bedrock (Claude 3 Haiku)
    • Genera PDF con fpdf2
    │
    ├──▶ S3: output/*.json  (metadata)
    ├──▶ S3: output/*.pdf   (PDF cuenta de cobro)
    └──▶ DynamoDB           (registro de estado)
    │
    ▼ S3 Event sobre *.pdf
    │
Lambda 3 — facturacion-sender
    • Construye email MIME con PDF adjunto
    • Envía por SES
    • Actualiza DynamoDB → "enviado"
    │
    ▼
📧 Destinatario recibe la cuenta de cobro
```

---

## Componentes

### Lambda 1 — `facturacion-trigger`

| Parámetro | Valor |
|-----------|-------|
| Trigger | S3 Event en `incoming/` |
| Runtime | Python 3.12 |
| Memoria | 256 MB |
| Timeout | 60 s |
| Layer | — (solo stdlib + boto3) |

**Flujo:**
1. Recibe evento S3 del email MIME guardado por SES.
2. Parsea el email y verifica que el asunto contenga `CUENTA DE COBRO`.
3. Si no coincide → archiva en `archived/` y termina.
4. Extrae el primer adjunto `.xlsx` / `.xls` y lo guarda en `processed/` con metadatos (remitente, asunto).

---

### Lambda 2 — `facturacion-orquestador`

| Parámetro | Valor |
|-----------|-------|
| Trigger | S3 Event en `processed/` |
| Runtime | Python 3.12 |
| Memoria | 512 MB |
| Timeout | 300 s |
| Layer | `hacksiesa-deps-full` (xlrd + openpyxl + fpdf2) |

**Variables de entorno requeridas:** `BUCKET_NAME`, `TABLE_NAME`, `MODEL_ID`, `PDF_BUCKET`, `DESTINATARIO`

**Flujo:**
1. Lee el Excel desde S3 (soporta `.xls` con `xlrd` y `.xlsx` con `openpyxl`).
2. Agrupa filas por `Nro documento`.
3. Por cada documento, invoca Bedrock (Claude 3 Haiku) con un system prompt estructurado.
4. Parsea la respuesta JSON del modelo.
5. Genera un PDF profesional con `fpdf2`.
6. Persiste JSON + PDF en S3 y registra el estado en DynamoDB.

---

### Lambda 3 — `facturacion-sender`

| Parámetro | Valor |
|-----------|-------|
| Trigger | S3 Event en `financial-*/output/*.pdf` |
| Runtime | Python 3.12 |
| Memoria | 256 MB |
| Timeout | 120 s |
| Layer | — (solo stdlib + boto3) |

**Variables de entorno requeridas:** `PDF_BUCKET`, `DATA_BUCKET`, `TABLE_NAME`, `SENDER_EMAIL`, `FORCE_DESTINATARIO`

**Flujo:**
1. Detecta el PDF generado por Lambda 2.
2. Lee el JSON de metadata para obtener `email_body` y destinatario.
3. Construye un email MIME multipart con el PDF adjunto.
4. Envía via SES.
5. Actualiza el registro en DynamoDB a estado `"enviado"`.

---

## Recursos AWS

| Recurso | Nombre / ARN |
|---------|--------------|
| S3 Emails | `hacksiesa-emails-us-east-1` |
| S3 PDFs | `financial-723595585512` |
| DynamoDB | `facturas-procesadas` (PK: `factura_id`) |
| SES Sender | `agente@hacksiesa.com` |
| SES Inbound | `inbound.hacksiesa.com` |
| Bedrock Model | `us.anthropic.claude-3-haiku-20240307-v1:0` |
| IAM Role | `hacksiesa-lambda-execution-role` |
| CFN Stack L1 | `hacksiesa-lambda-trigger` |
| CFN Stack L2 | `hacksiesa-lambda-orquestador` |
| CFN Stack L3 | `hacksiesa-lambda-sender` |

---

## Variables de entorno

Copiar `.env.example` como referencia. **Nunca commitear el `.env` real.**

```bash
cp .env.example .env
```

| Variable | Lambda | Descripción |
|----------|--------|-------------|
| `BUCKET_NAME` | L2 | Bucket principal (emails + processed + output JSON) |
| `TABLE_NAME` | L2, L3 | Tabla DynamoDB |
| `MODEL_ID` | L2 | ID del modelo Bedrock |
| `PDF_BUCKET` | L2, L3 | Bucket donde se guardan los PDFs generados |
| `DESTINATARIO` | L2 | Email destino por defecto |
| `DATA_BUCKET` | L3 | Bucket donde Lambda 3 lee los JSON |
| `SENDER_EMAIL` | L3 | Email verificado en SES para envíos |
| `FORCE_DESTINATARIO` | L3 | Sobreescribe destinatario (útil para pruebas) |

---

