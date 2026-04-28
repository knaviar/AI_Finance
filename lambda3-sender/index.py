"""
Lambda 3 — facturacion-sender
Trigger: S3 Event en financial-723595585512/output/*.pdf
Flujo: Lee JSON -> descarga PDF -> arma email MIME -> envia por SES -> actualiza DynamoDB
Env vars: PDF_BUCKET, DATA_BUCKET, TABLE_NAME, SENDER_EMAIL, FORCE_DESTINATARIO
"""
import boto3, json, os, re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
from urllib.parse import unquote_plus

s3 = boto3.client('s3')
ses = boto3.client('ses', region_name='us-east-1')
dynamodb = boto3.resource('dynamodb')

PDF_BUCKET = os.environ['PDF_BUCKET']
DATA_BUCKET = os.environ['DATA_BUCKET']
TABLE_NAME = os.environ['TABLE_NAME']
SENDER_EMAIL = os.environ['SENDER_EMAIL']
FORCE_DESTINATARIO = os.environ.get('FORCE_DESTINATARIO', '')

def lambda_handler(event, context):
    record = event['Records'][0]
    pdf_key = unquote_plus(record['s3']['object']['key'])
    bucket = record['s3']['bucket']['name']
    print(f"PDF detectado: {pdf_key} en {bucket}")

    if not pdf_key.lower().endswith('.pdf'):
        print(f"Ignorando {pdf_key}"); return {'statusCode': 200}

    filename = pdf_key.split('/')[-1]
    factura_id = filename.replace('.pdf', '')
    print(f"Factura ID: {factura_id}")

    table = dynamodb.Table(TABLE_NAME)
    try: db_item = table.get_item(Key={'factura_id': factura_id}).get('Item')
    except Exception as e: print(f"Error DynamoDB: {e}"); db_item = None

    email_body = None; destinatario = FORCE_DESTINATARIO; cliente_nombre = "Cliente"
    json_key = f"output/{factura_id}.json"
    try:
        json_obj = s3.get_object(Bucket=DATA_BUCKET, Key=json_key)
        agent_data = json.loads(json_obj['Body'].read())
        email_body = agent_data.get('email_body', '')
        if not destinatario:
            remitente_raw = agent_data.get('remitente', '')
            match = re.search(r'<(.+?)>', remitente_raw)
            destinatario = match.group(1) if match else remitente_raw
        pdf_content = agent_data.get('pdf_content', {})
        if pdf_content and isinstance(pdf_content, dict):
            cliente_nombre = pdf_content.get('cliente', {}).get('nombre', 'Cliente')
        print(f"JSON leido: destinatario={destinatario}, cliente={cliente_nombre}")
    except Exception as e:
        print(f"Error leyendo JSON: {e}")
        if db_item and not destinatario:
            rem = db_item.get('remitente', '')
            match = re.search(r'<(.+?)>', rem)
            destinatario = match.group(1) if match else rem

    if not destinatario:
        print("ERROR: No se encontro destinatario"); return {'statusCode': 400, 'body': 'Sin destinatario'}

    if not email_body:
        email_body = """<html><body style="font-family:Arial,sans-serif">
        <p>Estimado cliente,</p><p>Adjunto encontrara la cuenta de cobro correspondiente.</p>
        <p>Cordialmente,<br>SIESA HACK S.A.S</p></body></html>"""

    try:
        pdf_obj = s3.get_object(Bucket=bucket, Key=pdf_key)
        pdf_data = pdf_obj['Body'].read(); print(f"PDF descargado: {len(pdf_data):,} bytes")
    except Exception as e:
        print(f"Error descargando PDF: {e}"); return {'statusCode': 500}

    msg = MIMEMultipart('mixed')
    msg['Subject'] = f'Cuenta de cobro - {cliente_nombre}'
    msg['From'] = SENDER_EMAIL; msg['To'] = destinatario
    msg.attach(MIMEText(email_body, 'html', 'utf-8'))
    att = MIMEApplication(pdf_data)
    att.add_header('Content-Disposition', 'attachment',
        filename=f'cuenta_cobro_{cliente_nombre.replace(" ", "_")}.pdf')
    msg.attach(att)

    try:
        response = ses.send_raw_email(Source=SENDER_EMAIL, Destinations=[destinatario],
            RawMessage={'Data': msg.as_string()})
        message_id = response['MessageId']
        print(f"Email enviado! MessageId: {message_id}")
        print(f"  De: {SENDER_EMAIL} | Para: {destinatario} | Asunto: Cuenta de cobro - {cliente_nombre}")
    except Exception as e:
        print(f"Error SES: {e}")
        if db_item:
            table.update_item(Key={'factura_id': factura_id},
                UpdateExpression='SET estado = :s, error_envio = :e',
                ExpressionAttributeValues={':s': 'error_envio', ':e': str(e)})
        return {'statusCode': 500, 'body': str(e)}

    try:
        table.update_item(Key={'factura_id': factura_id},
            UpdateExpression='SET estado = :s, fecha_envio = :f, ses_message_id = :m',
            ExpressionAttributeValues={':s': 'enviado', ':f': datetime.now().isoformat(), ':m': message_id})
        print(f"DynamoDB actualizado: {factura_id} -> enviado")
    except Exception as e: print(f"Error actualizando DynamoDB: {e}")

    return {'statusCode': 200, 'factura_id': factura_id, 'destinatario': destinatario, 'ses_message_id': message_id}
