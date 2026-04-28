"""
Lambda 1 — facturacion-trigger
Trigger: S3 Event en incoming/ (email MIME recibido por SES)
Flujo: Filtra por asunto "CUENTA DE COBRO" -> Extrae Excel -> S3 processed/
"""
import boto3, email, uuid, json
from email import policy

s3 = boto3.client('s3')

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    if 'AMAZON_SES' in key:
        return {'statusCode': 200}

    raw = s3.get_object(Bucket=bucket, Key=key)['Body'].read()
    msg = email.message_from_bytes(raw, policy=policy.default)
    sender = str(msg['From'] or '')
    subject = str(msg['Subject'] or '')
    print(f'De: {sender} | Asunto: {subject}')

    filtro = 'CUENTA DE COBRO'
    if filtro not in subject.upper():
        print(f'IGNORADO: {subject}')
        s3.copy_object(Bucket=bucket, CopySource={'Bucket': bucket, 'Key': key},
                       Key=f'archived/{key.replace("incoming/","")}')
        s3.delete_object(Bucket=bucket, Key=key)
        return {'statusCode': 200}

    for part in msg.walk():
        filename = part.get_filename()
        if filename and filename.lower().endswith(('.xlsx', '.xls')):
            excel_data = part.get_payload(decode=True)
            if excel_data:
                excel_key = f'processed/{uuid.uuid4()}_{filename}'
                s3.put_object(Bucket=bucket, Key=excel_key, Body=excel_data,
                    Metadata={'remitente': sender[:256], 'asunto_original': subject[:256]})
                print(f'Excel: {excel_key}')
                break

    s3.copy_object(Bucket=bucket, CopySource={'Bucket': bucket, 'Key': key},
                   Key=f'archived/{key.replace("incoming/","")}')
    s3.delete_object(Bucket=bucket, Key=key)
    return {'statusCode': 200}
