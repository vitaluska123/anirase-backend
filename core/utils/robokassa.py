"""
Утилиты для работы с RoboKassa
"""
import hashlib
from django.conf import settings

def generate_payment_signature(login, amount, order_id, password1):
    """
    Генерирует подпись для создания платежа в RoboKassa
    
    Args:
        login (str): Логин магазина в RoboKassa
        amount (float): Сумма платежа
        order_id (int): ID заказа
        password1 (str): Пароль #1 из настроек RoboKassa
        
    Returns:
        str: Подпись в формате hex
    """
    signature_string = f"{login}:{amount}:{order_id}:{password1}"
    hash_algo = getattr(settings, 'ROBOKASSA_HASH_ALGO', 'sha256')
    
    if hash_algo == 'md5':
        return hashlib.md5(signature_string.encode('utf-8')).hexdigest()
    elif hash_algo == 'sha1':
        return hashlib.sha1(signature_string.encode('utf-8')).hexdigest()
    elif hash_algo == 'sha256':
        return hashlib.sha256(signature_string.encode('utf-8')).hexdigest()
    elif hash_algo == 'sha384':
        return hashlib.sha384(signature_string.encode('utf-8')).hexdigest()
    elif hash_algo == 'sha512':
        return hashlib.sha512(signature_string.encode('utf-8')).hexdigest()
    else:
        # По умолчанию SHA256
        return hashlib.sha256(signature_string.encode('utf-8')).hexdigest()

def generate_webhook_signature(out_sum, inv_id, password2):
    """
    Генерирует подпись для проверки webhook от RoboKassa
    
    Args:
        out_sum (str): Сумма платежа из webhook
        inv_id (str): ID заказа из webhook
        password2 (str): Пароль #2 из настроек RoboKassa
        
    Returns:
        str: Подпись в формате hex (uppercase)
    """
    signature_string = f"{out_sum}:{inv_id}:{password2}"
    hash_algo = getattr(settings, 'ROBOKASSA_HASH_ALGO', 'sha256')
    
    if hash_algo == 'md5':
        return hashlib.md5(signature_string.encode('utf-8')).hexdigest().upper()
    elif hash_algo == 'sha1':
        return hashlib.sha1(signature_string.encode('utf-8')).hexdigest().upper()
    elif hash_algo == 'sha256':
        return hashlib.sha256(signature_string.encode('utf-8')).hexdigest().upper()
    elif hash_algo == 'sha384':
        return hashlib.sha384(signature_string.encode('utf-8')).hexdigest().upper()
    elif hash_algo == 'sha512':
        return hashlib.sha512(signature_string.encode('utf-8')).hexdigest().upper()
    else:
        # По умолчанию SHA256
        return hashlib.sha256(signature_string.encode('utf-8')).hexdigest().upper()

def verify_webhook_signature(out_sum, inv_id, received_signature, password2):
    """
    Проверяет подпись webhook от RoboKassa
    
    Args:
        out_sum (str): Сумма платежа из webhook
        inv_id (str): ID заказа из webhook
        received_signature (str): Полученная подпись
        password2 (str): Пароль #2 из настроек RoboKassa
        
    Returns:
        bool: True если подпись верна, False если неверна
    """
    expected_signature = generate_webhook_signature(out_sum, inv_id, password2)
    return received_signature.upper() == expected_signature

def get_payment_url(login, amount, order_id, signature, description, email='', test_mode=True, success_url='', fail_url=''):
    """
    Формирует URL для оплаты в RoboKassa
    
    Args:
        login (str): Логин магазина
        amount (float): Сумма платежа
        order_id (int): ID заказа
        signature (str): Подпись
        description (str): Описание платежа
        email (str): Email покупателя
        test_mode (bool): Тестовый режим
        success_url (str): URL для успешной оплаты
        fail_url (str): URL для неуспешной оплаты
        
    Returns:
        str: URL для редиректа на оплату
    """
    params = {
        'MerchantLogin': login,
        'OutSum': str(amount),
        'InvId': str(order_id),
        'Description': description,
        'SignatureValue': signature,
        'Culture': 'ru',
    }
    
    if email:
        params['Email'] = email
        
    if success_url:
        params['SuccessURL'] = success_url
        
    if fail_url:
        params['FailURL'] = fail_url
        
    if test_mode:
        params['IsTest'] = '1'
    
    base_url = 'https://auth.robokassa.ru/Merchant/Index.aspx'
    query_string = '&'.join([f"{key}={value}" for key, value in params.items()])
    
    return f"{base_url}?{query_string}"

def verify_result_signature(out_sum, inv_id, signature):
    """
    Проверяет подпись результата платежа от RoboKassa
    
    Args:
        out_sum (str): Сумма платежа
        inv_id (str): ID заказа
        signature (str): Полученная подпись
        
    Returns:
        bool: True если подпись верна, False если неверна
    """
    password2 = getattr(settings, 'ROBOKASSA_PASSWORD2', '')
    if not password2:
        return False
        
    return verify_webhook_signature(out_sum, inv_id, signature, password2)
