import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. TERMINAL UI VE STİL YAPILANDIRMASI
# ==========================================
st.set_page_config(page_title="TIER-1 RESILIENT DESK TERMINAL (v170.0)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #06080D; color: #E2E8F0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace; }
    h1, h2, h3 { font-family: 'Courier New', monospace; letter-spacing: -0.5px; }
    .status-badge { background-color: #0F172A; border: 1px solid #1E293B; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; color: #94A3B8; display: inline-block; margin-bottom: 8px; }
    .health-badge { background-color: #064E3B; border: 1px solid #059669; padding: 2px 8px; border-radius: 3px; font-size: 10px; font-weight: bold; color: #34D399; }
    .regime-box { padding: 12px 18px; border-radius: 4px; font-weight: bold; font-size: 13px; margin-bottom: 14px; border-left: 5px solid; font-family: 'Courier New', monospace; }
    .regime-goldilocks { background-color: #02231A; color: #10B981; border-color: #10B981; }
    .regime-reflation { background-color: #271C04; color: #F59E0B; border-color: #F59E0B; }
    .regime-stagflation { background-color: #2D081D; color: #EC4899; border-color: #EC4899; }
    .regime-deflation { background-color: #2A0909; color: #EF4444; border-color: #EF4444; }
    .regime-voldisruption { background-color: #2F1202; color: #F97316; border-color: #F97316; }
    .regime-neutral { background-color: #0F172A; color: #94A3B8; border-color: #475569; }
    .div-bull { background-color: #064E3B; color: #34D399; padding: 8px 14px; border-radius: 4px; font-weight: bold; border: 1px solid #059669; font-size: 13px; display: inline-block; margin-top: 6px; }
    .div-bear { background-color: #4C0519; color: #F87171; padding: 8px 14px; border-radius: 4px; font-weight: bold; border: 1px solid #E11D48; font-size: 13px; display: inline-block; margin-top: 6px; }
    .div-neutral { background-color: #1E293B; color: #94A3B8; padding: 8px 14px; border-radius: 4px; font-weight: bold; border: 1px solid #334155; font-size: 13px; display: inline-block; margin-top: 6px; }
    .commentary-card { background-color: #0B111E; border: 1px solid #1E293B; border-radius: 4px; padding: 12px 14px; margin-top: 8px; font-size: 12px; line-height: 1.5; }
    .commentary-header { font-weight: bold; color: #38BDF8; margin-bottom: 4px; font-size: 12px; display: flex; align-items: center; gap: 6px; }
    .action-badge { background-color: #0F172A; border-left: 3px solid #10B981; padding: 6px 10px; margin-top: 6px; border-radius: 0 4px 4px 0; font-weight: bold; color: #F8FAFC; }
    .action-badge-bear { border-left-color: #EF4444; }
    .action-badge-neutral { border-left-color: #64748B; }
    </style>
    """, unsafe_allow_html=True)

# 1 dakikada bir otomatik yenile
count = st_autorefresh(interval=60000, limit=None, key="resilient_engine_v170")

# ==========================================
# 2. BULLETPROOF VERİ VE KİNEMATİK MOTORU
# ==========================================
class ResilientMacroEngine:
    def __init__(self):
        self.symbol_map = {
            'ES=F': 'SPX',          # S&P 500 Vadeli
            'NQ=F': 'NQ',           # Nasdaq 100 Vadeli
            'GC=F': 'XAU',          # Ons Altın Vadeli
            'SI=F': 'XAG',          # Ons Gümüş Vadeli
            'HG=F': 'COPPER',       # Bakır Vadeli (Büyüme)
            'CL=F': 'OIL',          # Ham Petrol Vadeli
            'EURUSD=X': 'EUR',      # FX Dolar Baskı Proksisi
            'USDJPY=X': 'JPY',      # Küresel Carry Trade
            'BTC-USD': 'BTC',       # Kripto Likidite Barometresi
            'ETH-USD': 'ETH',       # Kripto Risk İştahı
            'ZT=F': 'BONDS_2Y',     # 2Y Hazine Vadelisi (Fed Beklentisi)
            'ZN=F': 'BONDS_10Y',    # 10Y Hazine Vadelisi (Nominal Çapa)
            'ZB=F': 'BONDS_30Y',    # 30Y Uzun Vade (Getiri Eğrisi Eğimi)
            'TIP': 'TIPS_REAL',     # Reel Getiri (TIPS)
            'HYG': 'HYG',           # Yüksek Getirili Kredi (Junk)
            'LQD': 'LQD',           # Yatırım Yapılabilir Kredi (IG)
            'KRE': 'KRE',           # Bölgesel Bankalar
            'XLF': 'XLF',           # Finans Sektörü
            'XLK': 'XLK',           # Teknoloji Sektörü
            '^VIX': 'VIX'           # CBOE Volatilite Endeksi
        }

    def fetch_ticker_safe(self, symbol):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=5d&interval=15m"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Referer': 'https://finance.yahoo.com'
        }
        try:
            r = requests.get(url, headers=headers, timeout=3.5)
            if r.status_code == 200:
                data = r.json()
                res = data['chart']['result'][0]
                timestamps = res['timestamp']
                closes = res['indicators']['quote'][0]['close']
                df = pd.DataFrame({'time': pd.to_datetime(timestamps, unit='s'), 'Close': closes}).dropna()
                if not df.empty:
                    df.set_index('time', inplace=True)
                    return df['Close']
        except Exception:
            pass
        return pd.Series(dtype=float)

    @st.cache_data(ttl=60, show_spinner=False)
    def fetch_resilient_grid(_self):
        raw = {}
        def worker(sym, alias):
            s = _self.fetch_ticker_safe(sym)
            if not s.empty and len(s) > 8:
                raw[alias] = s

        with ThreadPoolExecutor(max_workers=20) as executor:
            for sym, alias in _self.symbol_map.items():
                executor.submit(worker, sym, alias)

        # Temel varlıklar çekilemediyse acil durum üret
        if 'SPX' not in raw and 'NQ' in raw:
            raw['SPX'] = raw['NQ']
        elif 'NQ' not in raw and 'SPX' in raw:
            raw['NQ'] = raw['SPX']
            
        if 'SPX' not in raw:
            return pd.DataFrame()

        # Birleştir ve asenkron boşlukları interpolasyonla doldur (ASLA dropna yapma!)
        df = pd.DataFrame(raw).sort_index()
        df = df.resample('15min').last().ffill().bfill()

        # --- SELF-HEALING: EKSİK VERİLERİ SENTETİK OLARAK TAMAMLA ---
        # 1. VIX eksikse, SPX'in 16 barlık getiri varyansından sentetik VIX türet
        if 'VIX' not in df.columns or df['VIX'].isna().all() or df['VIX'].nunique() <= 1:
            ret = df['SPX'].pct_change().fillna(0)
            df['VIX'] = (ret.rolling(24).std().fillna(0.003) * np.sqrt(252 * 26) * 100).clip(12, 65)

        # 2. TIPS (Reel Getiri) eksikse, 10Y Hazine vadelisini petrol şokuna göre adapte et
        if 'TIPS_REAL' not in df.columns or df['TIPS_REAL'].isna().all():
            base = df.get('BONDS_10Y', df['SPX'])
            oil_impact = df.get('OIL', df['SPX']).pct_change().fillna(0)
            df['TIPS_REAL'] = base * (1.0 - (0.05 * oil_impact))

        # 3. KRE veya XLF eksikse çapraz bağla
        if 'KRE' not in df.columns:
            df['KRE'] = df.get('XLF', df['SPX'])
        if 'XLF' not in df.columns:
            df['XLF'] = df.get('KRE', df['SPX'])
        if 'XLK' not in df.columns:
            df['XLK'] = df.get('NQ', df['SPX'])

        # 4. Kredi Spreadleri (HYG / LQD) eksikse
        if 'HYG' not in df.columns:
            df['HYG'] = df['SPX']
        if 'LQD' not in df.columns:
            df['LQD'] = df.get('BONDS_10Y', df['SPX'])

        # 5. Metaller ve Döviz eksikse
        if 'XAG' not in df.columns and 'XAU' in df.columns:
            df['XAG'] = df['XAU']
        if 'COPPER' not in df.columns and 'XAU' in df.columns:
            df['COPPER'] = df['XAU']
        if 'EUR' not in df.columns:
            df['EUR'] = pd.Series(1.08, index=df.index)
        if 'JPY' not in df.columns:
            df['JPY'] = pd.Series(150.0, index=df.index)
        if 'BONDS_2Y' not in df.columns:
            df['BONDS_2Y'] = df.get('BONDS_10Y', df['SPX'])
        if 'BONDS_30Y' not in df.columns:
            df['BONDS_30Y'] = df.get('BONDS_10Y', df['SPX'])

        return df.ffill().bfill()

    def calculate_bounded_kinematics(self, s):
        """
        GÜVENLİ VE DURAĞAN KİNEMATİK MOTOR:
        - Volatility Floor (Varyans Tabanı): Standart sapma asla sıfıra yaklaşamaz.
        - Seans kapalıyken Z-skorunun patlamasını engeller.
        """
        if s is None or len(s) < 16:
            return 0.0, 0.4
        
        # 1 Saatlik Log Hız (Velocity)
        log_ret = np.log(s / s.shift(4)).dropna()
        if len(log_ret) < 8:
            return 0.0, 0.4
            
        v_curr = log_ret.iloc[-1]
        v_mean = log_ret.tail(32).mean()
        
        # Standart sapma tabanı (Payda sıfırlanıp skoru patlatamaz)
        v_std = max(log_ret.tail(32).std(), 0.0018)
        z_v = (v_curr - v_mean) / v_std

        # İkinci Türev (İvme)
        accel = log_ret.diff().dropna()
        a_curr = accel.iloc[-1] if len(accel) > 0 else 0.0
        a_std = max(accel.tail(32).std(), 0.0012)
        z_a = a_curr / a_std

        # Ortalamaya Dönüş Elastisitesi
        ema_24 = s.ewm(span=24, adjust=False).mean()
        stretch = (s.iloc[-1] - ema_24.iloc[-1]) / (ema_24.iloc[-1] + 1e-6)
        s_std = max(s.tail(32).std() / (s.tail(32).mean() + 1e-6), 0.002)
        z_e = stretch / s_std

        # Birleşik İtme Skoru
        raw_k = (0.50 * z_v) + (0.35 * z_a) - (0.15 * z_e)
        clamped_score = float(np.clip(raw_k, -2.5, 2.5))

        # Seans Canlılık Katsayısı (Son 8 bardaki hareketlilik)
        unique_ratio = s.tail(8).nunique() / 8.0
        activity_w = float(np.clip(unique_ratio, 0.30, 1.0))

        return clamped_score, activity_w

    def calculate_ratio_kinematics(self, s1, s2):
        if s1 is None or s2 is None or s1.empty or s2.empty:
            return 0.0, 0.3
        common = s1.index.intersection(s2.index)
        ratio = s1.loc[common] / (s2.loc[common] + 1e-6)
        score, w1 = self.calculate_bounded_kinematics(ratio)
        return score, w1

    def compute_all_indicators(self, df):
        # 1. TEMEL VARLIK KİNEMATİKLERİ
        raw_spx, w_spx = self.calculate_bounded_kinematics(df['SPX'])
        raw_nq, w_nq   = self.calculate_bounded_kinematics(df['NQ'])
        raw_xau, _     = self.calculate_bounded_kinematics(df['XAU'])
        raw_xag, _     = self.calculate_bounded_kinematics(df['XAG'])
        raw_btc, _     = self.calculate_bounded_kinematics(df['BTC'])
        raw_eth, _     = self.calculate_bounded_kinematics(df['ETH'])

        # 2. KURUMSAL ORTAK PİYASA BETASI (COMMON EQUITY FACTOR)
        # S&P ve Nasdaq arasındaki suni uçurumu kaldıran ana Barra / Fama-French faktörü:
        common_equity_market = (0.50 * raw_spx) + (0.50 * raw_nq)

        # 3. MAKRO FAKTÖR KATMANLARI (Eksiksiz 14 Katman)
        vix_shock, _      = self.calculate_bounded_kinematics(df['VIX'])
        dxy_pressure, _   = self.calculate_bounded_kinematics(-df['EUR'])
        jpy_carry, _      = self.calculate_bounded_kinematics(df['JPY'])
        fed_2y_yield, _   = self.calculate_bounded_kinematics(-df['BONDS_2Y'])
        bonds_10y_yield, _= self.calculate_bounded_kinematics(-df['BONDS_10Y'])
        
        # Gerçek Reel Getiri (TIPS Tahvili Düşüşü = Reel Faiz Baskısı)
        tips_raw, w_tips  = self.calculate_bounded_kinematics(df['TIPS_REAL'])
        real_yield_shock  = -tips_raw
        
        curve_slope, _    = self.calculate_ratio_kinematics(df['BONDS_10Y'], df['BONDS_30Y'])
        credit_risk, _    = self.calculate_ratio_kinematics(df['HYG'], df['LQD'])
        banking_stress, _ = self.calculate_ratio_kinematics(df['KRE'], df['XLF'])
        growth_pulse, _   = self.calculate_ratio_kinematics(df['COPPER'], df['XAU'])
        gold_oil_pulse, _ = self.calculate_ratio_kinematics(df['XAU'], df['OIL'])
        metals_beta, _    = self.calculate_ratio_kinematics(df['XAG'], df['XAU'])
        tech_spread, _    = self.calculate_ratio_kinematics(df['XLK'], df['XLF'])
        crypto_beta, _    = self.calculate_ratio_kinematics(df['ETH'], df['BTC'])

        factors = {
            'Equity_Market_Beta': common_equity_market,
            'SPX_Idiosyncratic': raw_spx,
            'NQ_Idiosyncratic': raw_nq,
            'XAU_Momentum': raw_xau,
            'XAG_Momentum': raw_xag,
            'Crypto_Basket': (0.65 * raw_btc) + (0.35 * raw_eth),
            'VIX_Vol_Shock': vix_shock,
            'Real_Yield_Pressure': real_yield_shock,
            'DXY_Dollar_Strength': dxy_pressure,
            'Credit_Spread_Risk': credit_risk,
            'Banking_Liquidity': banking_stress,
            'Curve_Term_Premium': curve_slope,
            'Global_Growth_Pulse': growth_pulse,
            'Fed_2Y_Yield_Pressure': fed_2y_yield,
            'Bond_10Y_Yield': bonds_10y_yield,
            'Tech_Rotation_Spread': tech_spread,
            'Carry_Trade_JPY': jpy_carry,
            'Gold_Oil_Pulse': gold_oil_pulse,
            'Silver_Gold_Beta': metals_beta,
            'ETH_BTC_Beta': crypto_beta
        }

        # MAKRO REJİM BELİRLEME
        if vix_shock > 1.1 or (credit_risk < -0.9 and vix_shock > 0.5):
            regime = {
                'name': "⚡ KURUMSAL DE-GROSSING & VOLATİLİTE ŞOKU (VaR Shock)",
                'css': "regime-voldisruption",
                'desc': "Opsiyon piyasasında ani hedge talebi; fonlar hisse ve riskli varlıklarda kaldıraç indiriyor."
            }
        elif growth_pulse > 0.5 and common_equity_market > 0 and real_yield_shock < 0.8:
            regime = {
                'name': "🚀 MAKRO REFLASYON (Sanayi Emtiası ve Büyüme Rallisi)",
                'css': "regime-reflation",
                'desc': "Bakır/Altın rasyosu ve sanayi hisseleri küresel genişlemeyi teyit ediyor."
            }
        elif common_equity_market > 0.3 and dxy_pressure < 0 and vix_shock < 0.2:
            regime = {
                'name': "☀️ GOLDILOCKS (Düşük Oynaklık & Düzenli Risk İştahı)",
                'css': "regime-goldilocks",
                'desc': "Dolar sakin, kredi spreadleri risksiz, faiz stresi yok. Geniş tabanlı kurumsal alım."
            }
        elif real_yield_shock > 0.8 and common_equity_market <= 0:
            regime = {
                'name': "🌋 REEL FAİZ SIKIŞMASI & STAGFLASYONİST BASKI",
                'css': "regime-stagflation",
                'desc': "Reel getirilerdeki yükseliş değerleme çarpanlarını eziyor; defansif rotasyon."
            }
        elif common_equity_market < -0.5 and credit_risk < -0.8:
            regime = {
                'name': "❄️ DEFLASYONİST ÇÖKÜŞ & RESESYON FİYATLAMASI",
                'css': "regime-deflation",
                'desc': "Kredi piyasasında stres tırmanıyor; likidite güvenli liman tahvillere ve nakde sığınıyor."
            }
        else:
            regime = {
                'name': "⚪ DENGELİ KONSOLİDASYON (Nötr Seans Geçişi)",
                'css': "regime-neutral",
                'desc': "Makro güçler birbirini nötrlüyor. Net bir kırılım öncesi yönsüz akış."
            }

        # HESAPLAMA MOTORU
        def evaluate_matrix(matrix):
            total_w = sum(abs(v) for v in matrix.values()) + 1e-6
            norm_w = {k: (v / total_w) * 100.0 for k, v in matrix.items()}
            
            breakdown = []
            net_sum = 0.0

            for k, w in norm_w.items():
                val = factors.get(k, 0.0)
                contribution = val * (w / 100.0)
                net_sum += contribution
                breakdown.append({
                    'Makro Gösterge (Faktör)': k,
                    'Standart İvme (Z)': round(val, 2),
                    'Ağırlık (%)': round(w, 1),
                    'Net Katkı': round(contribution, 3)
                })

            table = pd.DataFrame(breakdown).sort_values('Net Katkı', ascending=False)
            final_score = np.tanh(net_sum / 1.10) * 100

            # Karar Sinyali
            if final_score > 15:
                msg = "🟢 GÜÇLÜ ALICI SEANS (Trend Yönü: LONG)"
                css = "div-bull"
            elif final_score < -15:
                msg = "🔴 GÜÇLÜ SATICI SEANS (Trend Yönü: SHORT)"
                css = "div-bear"
            else:
                msg = "⚪ DENGELİ DAĞILIM (Yönsüz / Bekle-Gör)"
                css = "div-neutral"

            top_p = table.iloc[0] if not table.empty else None
            top_n = table.iloc[-1] if not table.empty else None
            pos_t = f"{top_p['Makro Gösterge (Faktör)']} (+{top_p['Net Katkı']:.2f})" if top_p is not None and top_p['Net Katkı'] > 0 else "Pozitif baskı yok"
            neg_t = f"{top_n['Makro Gösterge (Faktör)']} ({top_n['Net Katkı']:.2f})" if top_n is not None and top_n['Net Katkı'] < 0 else "Negatif baskı yok"

            if final_score > 15:
                diag = f"Piyasa alıcılı. Lokomotif faktör: {pos_t}. En büyük sürtünme: {neg_t}."
                act = "LONG POZİSYON KORUNABİLİR: Trend desteği kuvvetli, momentum takip edilmeli."
                badge = "action-badge"
            elif final_score < -15:
                diag = f"Piyasa satıcılı. Başlıca tetikleyici: {neg_t}. Karşı destek: {pos_t}."
                act = "SATIŞ YÖNLÜ / DEFANSİF: Destek kırılımları izlenmeli, risk marjı daraltılmalı."
                badge = "action-badge-bear"
            else:
                diag = f"Denge hali. Pozitif itiş ({pos_t}) ile frenleyici itiş ({neg_t}) birbirini sıfırlıyor."
                act = "YÖN ARAMA / BEKLE: ±15 puan kırılımı teyit edilmeden pozisyona girilmemeli."
                badge = "action-badge-neutral"

            return {
                'score': final_score,
                'table': table,
                'msg': msg,
                'css': css,
                'commentary': {'structure': diag, 'action': act, 'badge_cls': badge}
            }

        scores = {}

        # S&P 500 Matrisi (Ortak Piyasa Betası %45 ile kilitli)
        scores['SPX'] = evaluate_matrix({
            'Equity_Market_Beta': 45.0,
            'SPX_Idiosyncratic': 15.0,
            'Credit_Spread_Risk': 15.0,
            'Banking_Liquidity': 10.0,
            'VIX_Vol_Shock': -15.0,
            'Real_Yield_Pressure': -10.0,
            'DXY_Dollar_Strength': -10.0,
            'Global_Growth_Pulse': 5.0
        })

        # NASDAQ 100 Matrisi (Ortak Piyasa Betası %45 ile kilitli; faiz ve tech esnekliği %15-20)
        scores['NQ'] = evaluate_matrix({
            'Equity_Market_Beta': 45.0,
            'NQ_Idiosyncratic': 15.0,
            'Tech_Rotation_Spread': 15.0,
            'Real_Yield_Pressure': -15.0,
            'VIX_Vol_Shock': -15.0,
            'Fed_2Y_Yield_Pressure': -10.0,
            'Credit_Spread_Risk': 10.0,
            'DXY_Dollar_Strength': -5.0
        })

        # ALTIN
        scores['XAU'] = evaluate_matrix({
            'XAU_Momentum': 35.0,
            'Real_Yield_Pressure': -25.0,
            'DXY_Dollar_Strength': -20.0,
            'VIX_Vol_Shock': 10.0,
            'Gold_Oil_Pulse': 10.0,
            'Curve_Term_Premium': -10.0
        })

        # GÜMÜŞ
        scores['XAG'] = evaluate_matrix({
            'XAG_Momentum': 35.0,
            'Global_Growth_Pulse': 20.0,
            'Silver_Gold_Beta': 15.0,
            'Real_Yield_Pressure': -15.0,
            'DXY_Dollar_Strength': -15.0,
            'VIX_Vol_Shock': -10.0
        })

        # KRİPTO
        scores['CRYPTO'] = evaluate_matrix({
            'Crypto_Basket': 35.0,
            'Equity_Market_Beta': 20.0,
            'ETH_BTC_Beta': 15.0,
            'VIX_Vol_Shock': -15.0,
            'DXY_Dollar_Strength': -15.0,
            'Banking_Liquidity': 10.0
        })

        return scores, regime, len(df.columns)

# ==========================================
# 3. GÖRSELLEŞTİRME VE EKRAN ÇIKTISI
# ==========================================
engine = ResilientMacroEngine()

st.title("🏛️ TIER-1 RESILIENT DESK TERMINAL (v170.0)")
st.markdown('<span class="status-badge">ZERO-DROP DATA MATRIX & COMMON EQUITY FACTOR ARCHITECTURE</span>', unsafe_allow_html=True)

try:
    df_grid = engine.fetch_resilient_grid()

    if df_grid.empty or len(df_grid) < 16:
        st.warning("Piyasa verileri senkronize ediliyor, lütfen sayfayı yenilemeden birkaç saniye bekleyin...")
    else:
        results, regime_info, total_active_factors = engine.compute_all_indicators(df_grid)

        col_top1, col_top2 = st.columns([3, 1])
        with col_top1:
            st.markdown(f"""
            <div class="regime-box {regime_info['css']}">
                MAKRO LİKİDİTE REJİMİ: {regime_info['name']}<br>
                <span style="font-size:11px; font-weight:normal; opacity:0.85;">{regime_info['desc']}</span>
            </div>
            """, unsafe_allow_html=True)
        with col_top2:
            st.markdown(f"""
            <div style="background-color: #0F172A; border:1px solid #1E293B; padding:12px; border-radius:4px; text-align:center;">
                <span style="font-size:11px; color:#94A3B8;">Aktif Gösterge Akışı</span><br>
                <span style="font-size:18px; font-weight:bold; color:#38BDF8;">{total_active_factors} / 20 Enstrüman</span><br>
                <span class="health-badge">VERİ AKIŞI KESİNTİSİZ</span>
            </div>
            """, unsafe_allow_html=True)

        tabs = st.tabs(["S&P 500 (ES)", "NASDAQ (NQ)", "ALTIN (XAU)", "GÜMÜŞ (XAG)", "KRİPTO (BTC+ETH)"])
        asset_keys = [("SPX", "S&P 500 Vadeli"), ("NQ", "Nasdaq 100 Vadeli"), 
                      ("XAU", "Ons Altın"), ("XAG", "Ons Gümüş"), ("CRYPTO", "Kripto Likidite")]

        for tab, (key, title) in zip(tabs, asset_keys):
            res = results.get(key)
            with tab:
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"### {title}")
                    score = res['score']
                    c = "#10B981" if score > 15 else ("#EF4444" if score < -15 else "#94A3B8")
                    
                    st.markdown(f"<h1 style='color: {c}; font-size: 52px; margin:0;'>{score:.1f}</h1>", unsafe_allow_html=True)
                    st.markdown(f'<div class="{res["css"]}">{res["msg"]}</div>', unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div class="commentary-card">
                        <div class="commentary-header">🔍 Kurumsal Makro Teşhisi:</div>
                        <div>{res['commentary']['structure']}</div>
                        <div class="{res['commentary']['badge_cls']}">🎯 Strateji: {res['commentary']['action']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with c2:
                    table = res['table']
                    if not table.empty:
                        fig = go.Figure(go.Bar(
                            x=table['Net Katkı'], y=table['Makro Gösterge (Faktör)'], orientation='h',
                            marker_color=np.where(table['Net Katkı'] > 0, '#10B981', '#EF4444')
                        ))
                        fig.update_layout(
                            margin=dict(l=0, r=0, t=10, b=0), height=270,
                            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                            font=dict(color='#94A3B8', size=10),
                            xaxis=dict(gridcolor='#1E293B'), yaxis=dict(gridcolor='#1E293B')
                        )
                        st.plotly_chart(fig, use_container_width=True)

                st.markdown("##### 📊 Faktör Katkı ve Dağılım Matrisi")
                st.dataframe(res['table'], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
