# app.py
import streamlit as st
import numpy as np
import math
import os
import requests
from datetime import datetime

st.set_page_config(page_title="Prop Challenge Calculator", layout="centered")

st.title("Prop Firm Challenge Calculator")
st.caption("Prop Challenge Pass Probability Simulator")

# -------------------------
# تنظیمات ارسال به Google Form
# -------------------------
# ترتیب اولویت: 1) st.secrets  2) متغیر محیطی
GOOGLE_FORM_URL = None
GOOGLE_ENTRY_EMAIL = None

if "GOOGLE_FORM_URL" in st.secrets:
    GOOGLE_FORM_URL = st.secrets["GOOGLE_FORM_URL"]
if "GOOGLE_ENTRY_EMAIL" in st.secrets:
    GOOGLE_ENTRY_EMAIL = st.secrets["GOOGLE_ENTRY_EMAIL"]

# fallback to environment variables (برای اجرأ لوکال)
if not GOOGLE_FORM_URL:
    GOOGLE_FORM_URL = os.environ.get("GOOGLE_FORM_URL")
if not GOOGLE_ENTRY_EMAIL:
    GOOGLE_ENTRY_EMAIL = os.environ.get("GOOGLE_ENTRY_EMAIL")

def submit_email_to_google_form(email, extra=None):
    """
    ارسال ایمیل به Google Form از طریق POST به آدرس formResponse.
    نیاز: GOOGLE_FORM_URL (مثلاً https://docs.google.com/forms/d/e/<FORM_ID>/formResponse)
          GOOGLE_ENTRY_EMAIL (مثلاً 'entry.1234567890')
    """
    if not GOOGLE_FORM_URL or not GOOGLE_ENTRY_EMAIL:
        return False, "آدرس فرم یا شناسه فیلد ایمیل تنظیم نشده است."

    payload = {
        GOOGLE_ENTRY_EMAIL: email
    }
    # در صورت تمایل فیلدهای اضافی را نیز ارسال کن، مثلاً زمان یا یک meta:
    if extra:
        payload["entry_extra"] = extra  # فقط نمونه؛ اگر در فرم فیلد معادل نداری، این خط را حذف کن

    try:
        # معمولاً Google Forms پاسخ 200 یا 302 می‌دهد؛ ما هر پاسخ غیرخطا را موفق در نظر می‌گیریم
        resp = requests.post(GOOGLE_FORM_URL, data=payload, timeout=10)
        if resp.status_code in (200, 302):
            return True, None
        else:
            return False, f"کد پاسخ {resp.status_code}"
    except Exception as e:
        return False, str(e)

# -------------------------
# فرم ورودی‌ها (اضافه‌شدن فیلد ایمیل)
# -------------------------
with st.form("inputs"):
    col1, col2 = st.columns(2)
    with col1:
        email = st.text_input("ایمیل خود را وارد کنید:")
        win_rate = st.slider("درصد برد (Win rate %) (%)", min_value=1, max_value=99, value=40, step=1)
        risk_reward = st.number_input("ریسک به ریوارد (مثلاً 2 یعنی ریوارد=2×ریسک)", min_value=0.1, value=2.0, step=0.1, format="%.2f")
        risk_per_trade_pct = st.slider("درصد ریسک در هر ترید (%)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
        challenge_type = st.selectbox("نوع چالش", options=["تک‌مرحله‌ای", "دو‌مرحله‌ای"])
    with col2:
        if challenge_type == "دو‌مرحله‌ای":
            profit_target_p1 = st.number_input("تارگت سود فاز ۱ (%)", min_value=0.1, value=10.0, step=0.1)
            profit_target_p2 = st.number_input("تارگت سود فاز ۲ (%)", min_value=0.1, value=5.0, step=0.1)
        else:
            profit_target_p1 = st.number_input("تارگت سود (%)", min_value=0.1, value=10.0, step=0.1)
            profit_target_p2 = None
        max_drawdown_pct = st.number_input("حداکثر دراودان مجاز (%)", min_value=0.1, value=10.0, step=0.1)
        challenge_fee = st.number_input("هزینه هر چالش / Attempt ($)", min_value=0.0, value=500.0, step=1.0)
        account_size = st.number_input("اندازه حساب (دلاری) — فقط برای نمایش (اختیاری)", min_value=0.0, value=100000.0, step=1.0)
        simulations = st.number_input("تعداد شبیه‌سازی (Monte Carlo)", min_value=100, max_value=200000, value=5000, step=100)
        max_trades = st.number_input("حداکثر ترید در هر شبیه‌سازی", min_value=10, max_value=10000, value=500, step=10)

    submitted = st.form_submit_button("اجرا کن")

# توابع شبیه‌سازی (همان قبلی)
def run_phase_once(win_rate, rr, risk_pct, profit_target_pct, max_dd_pct, max_trades):
    win_p = win_rate / 100.0
    risk = risk_pct / 100.0
    profit_target = profit_target_pct / 100.0
    max_dd = max_dd_pct / 100.0

    balance = 1.0
    peak = 1.0

    for i in range(int(max_trades)):
        if np.random.rand() < win_p:
            balance *= (1.0 + risk * rr)
        else:
            balance *= (1.0 - risk)
        if balance > peak:
            peak = balance
        drawdown = 1.0 - (balance / peak)
        if (balance - 1.0) >= profit_target:
            return True, i + 1
        if drawdown >= max_dd:
            return False, i + 1
    return False, int(max_trades)

def simulate(win_rate, rr, risk_pct, p1, p2, max_dd_pct, sims, max_trades, two_phase):
    pass_count = 0
    trades_list = []
    for _ in range(int(sims)):
        p1_passed, t1 = run_phase_once(win_rate, rr, risk_pct, p1, max_dd_pct, max_trades)
        if two_phase:
            if not p1_passed:
                continue
            p2_passed, t2 = run_phase_once(win_rate, rr, risk_pct, p2, max_dd_pct, max_trades)
            if p2_passed:
                pass_count += 1
                trades_list.append(t1 + t2)
        else:
            if p1_passed:
                pass_count += 1
                trades_list.append(t1)
    pass_rate = pass_count / sims
    avg_trades = np.mean(trades_list) if trades_list else 0.0
    return pass_rate, avg_trades

# -------------------------
# اجرا: ارسال ایمیل به Google Form و سپس شبیه‌سازی
# -------------------------
if submitted:
    # بررسی ایمیل (خالی نباشد + معتبر باشد)
    import re
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    
    if not email or not re.match(email_pattern, email):
        st.error("لطفاً یک ایمیل معتبر وارد کنید.")
        st.stop()

    # ارسال به Google Form
    success, error = submit_email_to_google_form(email, extra=f"winrate={win_rate},rr={risk_reward}")
    if not success:
        st.error("ثبت ایمیل انجام نشد — لطفاً ایمیل را به درستی وارد کنید.")
        st.stop()

    st.success("ایمیل شما با موفقیت ثبت شد ✅ شبیه‌سازی در حال انجام است...")

    # ادامهٔ نمایش شبیه‌سازی (همان قبلی)
    st.write("درحال اجرا... (صبر کنید تا شبیه‌سازی تمام شود)")
    two_phase = (challenge_type == "دو‌مرحله‌ای")
    p1 = profit_target_p1
    p2 = profit_target_p2 if two_phase else None

    pass_rate, avg_trades = simulate(
        win_rate=win_rate,
        rr=risk_reward,
        risk_pct=risk_per_trade_pct,
        p1=p1,
        p2=p2 if p2 is not None else 0.0,
        max_dd_pct=max_drawdown_pct,
        sims=simulations,
        max_trades=max_trades,
        two_phase=two_phase
    )

    st.subheader("نتایج شبیه‌سازی")
    st.markdown(f"- ✅ **احتمال پاس شدن چالش:** `{pass_rate*100:.2f}%`")
    st.markdown(f"- 📈 **میانگین تعداد ترید تا پاس (اگر پاس شود):** `{avg_trades:.1f}`")

    if pass_rate > 0:
        expected_attempts = 1.0 / pass_rate
        attempts_ceil = math.ceil(expected_attempts)
        total_cost_ceil = attempts_ceil * challenge_fee
        st.markdown(f"- 🔁 **تعداد تلاش مورد انتظار :** `{expected_attempts:.2f}`")
        st.markdown(f"- 🔼 **تعداد تلاش خریدنی :** `{attempts_ceil}`")
        st.markdown(f"- 💰 **هزینهٔ قابل پرداخت :** `${total_cost_ceil:,.0f}`")
    else:
        st.markdown("- ⚠️ با این پارامترها احتمال پاس صفر است؛ نیاز به تغییر ورودی‌ها دارید.")

    st.markdown("---")
    st.caption("توضیح: برای هزینهٔ قابل پرداخت، مقدار تلاش‌های مورد نیاز به بالا گرد می‌شود (ceil).")




    # =======================
    # 🌐 Clickable Image
    # =======================
    image_url = "https://i.postimg.cc/dVmcGc0j/ytchannel.jpg"
    link_url = "https://www.youtube.com/@zareii.Abbass/videos"

    st.markdown(
        f"""
        <a href="{link_url}" target="_blank">
            <img src="{image_url}" width="400" style="display:block; margin:auto;">
        </a>
        """,
        unsafe_allow_html=True
    )

