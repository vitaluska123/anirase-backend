from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from core.models import EmailAccount
import imaplib
import email
from email.header import decode_header
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import smtplib
from email.mime.text import MIMEText
from django.apps import apps

MAIL_TEMPLATES = [
    "Спасибо за обращение! Мы рассмотрим ваш вопрос в ближайшее время.",
    "Ваше письмо получено. Ожидайте ответа от нашей команды.",
    "Здравствуйте! Спасибо за ваш интерес. Мы свяжемся с вами в течение дня."
]

def fetch_emails(account: EmailAccount, limit=10):
    mails = []
    try:
        mail = imaplib.IMAP4_SSL(account.imap_server, account.imap_port)
        mail.login(account.email, account.password)
        mail.select('INBOX')
        typ, data = mail.search(None, 'ALL')
        mail_ids = data[0].split()[-limit:]
        for num in reversed(mail_ids):
            typ, msg_data = mail.fetch(num, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])
            subject, encoding = decode_header(msg['Subject'])[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding or 'utf-8', errors='ignore')
            from_ = msg.get('From', '')
            date_ = msg.get('Date', '')
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')
            mails.append({
                'uid': num.decode(),
                'subject': subject,
                'from': from_,
                'date': date_,
                'body': body,
            })
        mail.logout()
    except Exception as e:
        mails.append({'subject': f'Ошибка: {e}', 'from': '', 'date': '', 'body': ''})
    return mails

def send_reply(account: EmailAccount, to_addr, subject, body):
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = account.email
    msg['To'] = to_addr
    with smtplib.SMTP_SSL(account.smtp_server, account.smtp_port) as server:
        server.login(account.email, account.password)
        server.sendmail(account.email, [to_addr], msg.as_string())

@staff_member_required
def report_dashboard(request):
    # Получаем все модели core
    core_models = apps.get_app_config('core').get_models()
    model_names = [m.__name__ for m in core_models]
    selected_model = request.GET.get('model')
    data = []
    fields = []
    if selected_model:
        Model = apps.get_model('core', selected_model)
        fields = [f.name for f in Model._meta.fields]
        data = list(Model.objects.all().values())[:1000]
    return render(request, 'admin/report_dashboard.html', {
        'model_names': model_names,
        'selected_model': selected_model,
        'fields': fields,
        'data': data,
    })

@staff_member_required
@csrf_exempt
def report_mail_dashboard(request):
    accounts = EmailAccount.objects.filter(is_active=True)
    selected_account_id = request.GET.get('account') or (accounts[0].id if accounts else None)
    selected_account = accounts.filter(id=selected_account_id).first() if selected_account_id else None
    emails = fetch_emails(selected_account) if selected_account else []
    selected_mail = None
    reply_body = ''
    if request.method == 'GET' and request.GET.get('mail_id'):
        mail_id = request.GET['mail_id']
        for mail in emails:
            if mail['uid'] == mail_id:
                selected_mail = mail
                reply_body = f"\n\n---\n{mail['body'][:200]}"
                break
    if request.method == 'POST' and selected_account:
        mail_id = request.GET.get('mail_id')
        if mail_id:
            for mail in emails:
                if mail['uid'] == mail_id:
                    selected_mail = mail
                    break
            reply_body = request.POST.get('reply_body', '')
            template = request.POST.get('template', '')
            if template:
                reply_body = template + "\n\n" + reply_body
            send_reply(selected_account, selected_mail['from'], f"Re: {selected_mail['subject']}", reply_body)
            return redirect(request.path + f'?account={selected_account_id}')
        # --- Новый функционал: отправка нового письма ---
        if request.GET.get('new_mail'):
            to = request.POST.get('to', '').strip()
            subject = request.POST.get('subject', '').strip()
            body = request.POST.get('body', '').strip()
            template = request.POST.get('template', '').strip()
            if template:
                body = template + "\n\n" + body
            # поддержка нескольких адресов через запятую
            to_list = [x.strip() for x in to.split(',') if x.strip()]
            for email_addr in to_list:
                send_reply(selected_account, email_addr, subject, body)
            return redirect(request.path + f'?account={selected_account_id}')
    return render(request, 'admin/report_mail_dashboard.html', {
        'accounts': accounts,
        'selected_account_id': int(selected_account_id) if selected_account_id else None,
        'emails': emails,
        'selected_mail': selected_mail,
        'templates': MAIL_TEMPLATES,
        'reply_body': reply_body,
    })
