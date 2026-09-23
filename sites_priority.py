# -*- coding: utf-8 -*-
"""
سایت‌های اولویت بالا - ۱۰۰٪ کار می‌کنند
این لیست همیشه اول تست می‌شود
"""

PRIORITY_SITES = [
    # ═══ جدیدترین (تضمین‌شده) ═══
    ("https://tondton.com/auth", "تندتن", "gold", 1),
    ("https://app.tetherland.com/login", "تترلند", "crypto", 1),
    ("https://gapgpt.app/login", "تترلند", "crypto", 1),
    ("https://www.shop.ir/sign-in?backUrl=%2Fprofile", "shop;", "shop", 1),
    ("https://tapsi.shop/auth/signin?step=checkPhoneNumber", "tapsi shop", "shop", 1),
    ("https://reymit.ir/register/", "donate" , "ss" , 1),
    

    # ═══ بدون کپچا - تست‌شده ═══
    ("https://api.snapp.ir/api/v1/sms/link", "اسنپ", "no_captcha", 2),
    ("https://app.snapp.taxi/api/api-passenger-oauth/v2/otp", "اسنپ تاکسی", "no_captcha", 2),
    ("https://api.divar.ir/v5/auth/authenticate", "دیوار", "no_captcha", 2),
    ("https://www.sheypoor.com/api/v10.0.0/auth/send", "شیپور", "no_captcha", 2),
    ("https://api.digikala.com/v1/user/authenticate/", "دیجی‌کالا", "no_captcha", 2),
    ("https://ws.alibaba.ir/api/v3/account/mobile/otp", "علی‌بابا", "no_captcha", 2),
    ("https://api.tapsi.ir/api/v2.2/user", "تپسی", "no_captcha", 2),
    ("https://tap33.me/api/v2/user", "تپ۳۳", "no_captcha", 2),
    ("https://api.achareh.co/v2/accounts/login/", "آچاره", "no_captcha", 2),
    ("https://gw.jabama.com/api/v4/account/send-code", "جاباما", "no_captcha", 2),
    ("https://mobapi.banimode.com/api/v2/auth/request", "بانی‌مد", "no_captcha", 2),
    ("https://api.mootanroo.com/api/v3/auth/send-otp", "متنرو", "no_captcha", 2),
    ("https://api.lendo.ir/api/customer/auth/send-otp", "لندو", "no_captcha", 2),

    # ═══ طلا و صرافی تست‌شده ═══
    ("https://api.melligold.com/api/v1/auth/send-otp", "ملی‌گلد", "gold", 2),
    ("https://my.tlyn.ir/api/v1/auth/send-otp", "طلاین", "gold", 2),
    ("https://api.wallex.ir/api/v1/auth/send-otp", "والکس", "crypto", 2),
    ("https://api.nobitex.ir/v2/auth/login/otp", "نوبیتکس", "crypto", 2),
    ("https://api.bitpin.org/api/v1/auth/send-otp", "بیت‌پین", "crypto", 2),
    ("https://api.tabdeal.org/api/v1/auth/send-otp", "تب‌دیل", "crypto", 2),
]


def get_priority_sites():
    return list(PRIORITY_SITES)


def get_priority_urls():
    return [s[0] for s in PRIORITY_SITES]
