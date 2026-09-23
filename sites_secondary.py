# -*- coding: utf-8 -*-
"""
سایت‌های ذخیره - اگر اولویت‌دارها تمام شدند
"""

SECONDARY_SITES = [
    # طلا
    ("https://api.talasea.ir/api/v1/auth/send-otp", "طلاسی", "gold"),
    ("https://api.tala.ir/api/v1/auth/send-otp", "طلا دات آی‌آر", "gold"),
    ("https://api.wallgold.ir/api/v1/auth/send-otp", "وال‌گلد", "gold"),
    ("https://api.daric.gold/api/v1/auth/send-otp", "داریک گلد", "gold"),
    ("https://api.goldika.ir/api/v1/auth/send-otp", "گلدیکا", "gold"),
    ("https://api.milli.gold/api/v1/auth/send-otp", "میلی گلد", "gold"),
    ("https://api.zarpad.ir/api/v1/auth/send-otp", "زرپاد", "gold"),
    ("https://api.technogold.ir/api/v1/auth/send-otp", "تکنوگلد", "gold"),
    ("https://api.tokeniko.ir/api/v1/auth/send-otp", "توکنیکو", "gold"),
    ("https://api.invi.ir/api/v1/auth/send-otp", "اینوی", "gold"),
    ("https://api.zarafza.ir/api/v1/auth/send-otp", "زرافزا", "gold"),
    ("https://api.zarpey.ir/api/v1/auth/send-otp", "زرپی", "gold"),
    ("https://melligold.com/api/v1/auth/send-otp", "ملی‌گلد مستقیم", "gold"),
    ("https://app.tlyn.ir/api/v1/auth/send-otp", "طلاین اپ", "gold"),

    # صرافی
    ("https://apiv2.nobitex.ir/v2/auth/login/otp", "نوبیتکس v2", "crypto"),
    ("https://api.wallex.ir/api/v1/auth/otp", "والکس v2", "crypto"),
    ("https://api.bitpin.org/api/v1/auth/otp", "بیت‌پین v2", "crypto"),
    ("https://api.ramzinex.com/exchange/api/v1.0/auth/send-otp", "رمزینکس", "crypto"),
    ("https://api.abantether.com/api/v1/auth/send-otp", "آبان‌تتر", "crypto"),
    ("https://api.arzinja.ir/api/v1/auth/send-otp", "ارزینجا", "crypto"),
    ("https://api.bit24.cash/api/v1/auth/send-otp", "بیت۲۴", "crypto"),
    ("https://api.exir.io/api/v1/auth/send-otp", "اکسیر", "crypto"),
    ("https://api.pay98.com/api/v1/auth/send-otp", "پی۹۸", "crypto"),
    ("https://api.coin.ir/api/v1/auth/send-otp", "کوین دات آی‌آر", "crypto"),
    ("https://api.parsbit.com/api/v1/auth/send-otp", "پارس‌بیت", "crypto"),
    ("https://api.ajax-finance.com/api/v1/auth/send-otp", "آجاکس", "crypto"),
    ("https://api.asa-coin.com/api/v1/auth/send-otp", "آساکوین", "crypto"),
    ("https://api.bitmax.ir/api/v1/auth/send-otp", "بیت‌مکس", "crypto"),
    ("https://api.poolno.com/api/v1/auth/send-otp", "پولنو", "crypto"),
    ("https://api.altax.ir/api/v1/auth/send-otp", "آلتاکس", "crypto"),
    ("https://api.bitsubit.com/api/v1/auth/send-otp", "بیت‌سابیت", "crypto"),
    ("https://api.zarindex.com/api/v1/auth/send-otp", "زرایندکس", "crypto"),

    # سایر سرویس‌ها
    ("https://app.itoll.com/api/v1/auth/login", "ایتول", "service"),
    ("https://my.okcs.com/api/check-mobile", "OKCS", "service"),
    ("https://www.tebinja.com/api/v1/users", "تبینجا", "service"),
    ("https://appapi.sms.ir/api/app/auth/sign-up/verification-code", "SMS.ir", "sms"),
    ("https://api.sms.ir/v1/send/verify", "SMS.ir v2", "sms"),
    ("https://api2.ippanel.com/api/v1/sms/pattern/normal/send", "IPPanel", "sms"),
    ("https://api.kavenegar.com/v1/", "کاوه‌نگار", "sms"),
    ("https://api.melipayamak.com/", "ملی‌پیامک", "sms"),
    ("https://api.ghasedak.me/v2/", "قاصدک", "sms"),
    ("https://api.farapayamak.ir/", "فراپیامک", "sms"),
    ("https://safir.bale.ai/api/v3/send_message", "بله", "service"),
    ("https://next.zarinpal.com/api/oauth/register", "زرین‌پال", "service"),
    ("https://api.zarinpal.com/", "زرین‌پال v2", "service"),
    ("https://api.snappfood.ir/", "اسنپ‌فود", "food"),
    ("https://api.snappmarket.ir/", "اسنپ‌مارکت", "food"),
    ("https://api.snappexpress.ir/", "اسنپ‌اکسپرس", "food"),
    ("https://api.snapptrip.com/", "اسنپ‌تریپ", "travel"),
    ("https://api.digistyle.com/", "دیجی‌استایل", "ecommerce"),
    ("https://api.takhfifan.com/", "تخفیفان", "ecommerce"),
    ("https://api.bamilo.com/", "بامیلو", "ecommerce"),
    ("https://api.modiseh.com/", "مدیسه", "ecommerce"),
    ("https://api.filimo.com/", "فیلیمو", "service"),
    ("https://api.aparat.com/", "آپارات", "service"),
    ("https://api.cafebazaar.ir/", "کافه‌بازار", "service"),
    ("https://api.myket.ir/", "مایکت", "service"),
    ("https://api.sibapp.ir/", "سیب‌اپ", "service"),
    ("https://api.charkhoneh.com/", "چارخونه", "service"),
    ("https://www.namava.ir/api/v1.0/accounts/registrations/by-phone/request", "نماوا", "service"),
    ("https://www.hamrah-mechanic.com/api/v1/membership/otp", "همراه مکانیک", "service"),
    ("https://student.classino.com/otp/v1/api/login", "کلاسینو", "service"),
    ("https://nobat.ir/api/public/patient/login/phone", "نوبت", "service"),
]


def get_secondary_sites():
    return list(SECONDARY_SITES)


def get_secondary_urls():
    return [s[0] for s in SECONDARY_SITES]