import streamlit as st
import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. UI VE TERMINAL YAPILANDIRMASI
# ==========================================
st.set_page_config(page_title="TIER-1 ADAPTIVE QUANT TERMINAL (v150.3-PRO)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { font-family: 'Courier New', monospace; font-size: 22px; }
    h2, h3 { color: #ECEFF1; font-size: 15px; }
    .regime-box { padding: 12px 18px; border-radius: 6px; font-weight: bold; font-size: 13px; margin-bottom: 12px; border-left: 5px solid; }
    .regime-bull { background-color: #00332c; color: #00E676; border-color: #00E676; }
    .regime-bear { background-color: #330000; color: #FF1744; border-color: #FF1744; }
    .regime-crisis { background-color: #4A0000; color: #FF5252; border-color: #FF1744; animation: blink 1.5s infinite; }
    .regime-mixed { background-color: #262000; color: #FFB300; border-color: #FFB300; }
    .div-bull { background-color: #004D40; color: #00E676; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #00E676; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-bear { background-color: #4A148C; color: #FF1744; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #FF1744; font-size: 13px; display: inline-block; margin-top: 5px; }
    .div-short-lock { background-color: #B71C1C; color: #FFFFFF; padding: 6px 12px; border-radius: 4px; font-weight: bold; border: 1px solid #FF5252; font-size: 13px; display: inline-block; margin-top: 5px; }
    .commentary-card { background-color: #121824; border: 1px solid #2A364F; border-radius: 6px; padding: 12px 16px; margin-top: 10px; font-size: 13px; line-height: 1.6; }
    .commentary-header { font-weight: bold; color: #64B5F6; margin-bottom: 4px; font-size: 13px; display: flex; align-items: center; gap: 6px; }
    .action-badge { background-color: #1E293B; border-left: 3px solid #00E676; padding: 6px 10px; margin-top: 6px; border-radius: 0 4px 4px 0; font-weight: bold; color: #F8FAFC; }
    .action-badge-bear { border-left-color: #FF1744; background-color: #1E293B; }
    </style>
    """, unsafe_allow_html=True)

# 1 dakikada bir otomatik yenile
st_autorefresh(interval=60000, limit=None, key="macro_refresh_1503")

# ==========================================
# 2. TAM DİNAMİK VE ADAPTİF QUANT MOTORU
# ==========================================
class FullyAdaptiveQuantEngine:
    def __init__(self):
        self.symbol_map = {
            'ES=F': 'SPX', 'NQ=F': 'NQ', 'GC=F': 'XAU', 'SI=F': 'XAG',
            'HG=F': 'COPPER', 'CL=F': 'OIL', 'EURUSD=X': 'EUR',
            'USDJPY=X': 'JPY', 'BTC-USD': 'BTC', 'ETH-USD': 'ETH',
            'ZT=F': 'BONDS_2Y', 'ZN=F': 'BONDS_10Y', 'ZB=F': 'BONDS_30Y',
            'HYG': 'HYG', 'LQD': 'LQD', 'KRE': 'KRE', 'XLK': 'XLK',
            'XLF': 'XLF', 'RSP': 'RSP', 'XME': 'XME'
        }
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))

    def fetch_single_ticker(self, symbol):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=10d&interval=15m"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        try:
            r = self.session.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                res = r.json()['chart']['result'][0]
                df = pd.DataFrame({
                    'time': pd.to_datetime(res['timestamp'], unit='s'),
                    'Close': res['indicators']['quote'][0]['close']
                }).dropna().set_index('time')
                return df['Close']
        except Exception:
            pass
        return pd.Series(dtype=float)

    @st.cache_data(ttl=60, show_spinner=False)
    def fetch_synchronized_grid(_self):
        raw_dict = {}
        def worker(sym, alias):
            s = _self.fetch_single_ticker(sym)
            if not s.empty:
                raw_dict[alias] = s

        with ThreadPoolExecutor(max_workers=6) as executor:
            for sym, alias in _self.symbol_map.items():
                executor.submit(worker, sym, alias)

        df = pd.DataFrame(raw_dict).sort_index()
        return df.resample('15min').last().ffill().bfill().dropna()

    # Dynamic Rolling Z-Score Math
    def compute_rolling_z(self, series, window=64):
        if series is None or len(series) < 10:
            return 0.0
        pct = series.pct_change().dropna()
        mean = pct.rolling(window=window, min_periods=5).mean()
        std = pct.rolling(window=window, min_periods=5).std().replace(0, 1e-6)
        z = (pct - mean) / std
        return float(np.clip(z.iloc[-1] if not z.empty else 0.0, -3.5, 3.5))

    # Dynamic Ratio Compute
    def compute_ratio_z(self, s1, s2, window=64):
        if s1 is None or s2 is None or s1.empty or s2.empty:
            return 0.0
        idx = s1.index.intersection(s2.index)
        ratio = s1.loc[idx] / (s2.loc[idx] + 1e-6)
        return self.compute_rolling_z(ratio, window)

    # Sigmoid Normalization (Dynamic Bound)
    def sigmoid_smooth(self, val, k=1.5):
        return float(np.tanh(val / k))

    def evaluate_system_stresses(self, df):
        # Makro ve Sistemik Stres Vektörleri
        credit_stress = -self.compute_ratio_z(df['HYG'], df['LQD'])  # Yüksek Getirili Kredi Stresi
        funding_stress = -self.compute_ratio_z(df['KRE'], df['XLF']) # Bankacılık Likidite Stresi
        yield_shock = self.compute_rolling_z(df['BONDS_10Y'])       # Tahvil Faiz Sıçraması
        dxy_shock = -self.compute_rolling_z(df['EUR'])               # Dolar Gücü Sıçraması
        
        # Çok Değişkenli Anomali Skoru (Anomali Engine)
        stress_vector = np.array([credit_stress, funding_stress, yield_shock, dxy_shock])
        anomali_score = float(np.linalg.norm(stress_vector) / 2.0)
        
        is_crisis = anomali_score > 1.85 or credit_stress > 2.2 or funding_stress > 2.2
        return {
            'credit_stress': credit_stress,
            'funding_stress': funding_stress,
            'yield_shock': yield_shock,
            'dxy_shock': dxy_shock,
            'anomali_score': anomali_score,
            'is_crisis': is_crisis
        }

    def process_asset_analysis(self, df, asset_name, factor_matrix, stresses):
        """
        DİNAMİK TERS KORELASYON VE ADAPTİF AĞIRLIKLANDIRMA
        factor_matrix yapısı:
        {
          'Factor_Name': {'val': float, 'dir': +1 or -1 (Ters Korelasyon Vektörü), 'weight': float}
        }
        """
        breakdown = []
        raw_score = 0.0
        total_weight = 0.0

        for f_name, f_data in factor_matrix.items():
            raw_z = f_data['val']
            direction = f_data['dir'] # +1 doğrudan korelasyon, -1 ters korelasyon
            base_w = f_data['weight']

            # Ters korelasyon otomatik yön matrisi ile çarpılır
            effective_impact = self.sigmoid_smooth(raw_z) * direction
            
            # Dinamik Kriz Ağırlıklandırması (Kriz anında risk göstergelerinin ağırlığı katlanır)
            if stresses['is_crisis'] and ('Stress' in f_name or 'Risk' in f_name or 'Yield' in f_name):
                dyn_w = base_w * 2.5
            else:
                dyn_w = base_w

            contrib = effective_impact * dyn_w
            raw_score += contrib
            total_weight += dyn_w

            breakdown.append({
                'Faktör Katmanı': f_name,
                'Z-Skor': round(raw_z, 2),
                'Korelasyon Yönü': 'Doğrudan (+)' if direction > 0 else 'Ters (-)',
                'Dinamik Etki': round(effective_impact, 2),
                'Katkı': round(contrib, 3)
            })

        breakdown_df = pd.DataFrame(breakdown).sort_values('Katkı', ascending=False)
        
        normalized_score = (raw_score / (total_weight + 1e-6)) * 100.0
        final_score = float(np.clip(normalized_score, -100.0, 100.0))

        # KRİZ / ANOMALİ ANINDA SHORT KİLİTLEME DİSİPLİNİ
        if stresses['is_crisis'] and asset_name in ['SPX', 'NQ', 'CRYPTO', 'XAG']:
            # Yüksek beta riskli varlıklarda skoru doğrudan Short bölgesine kilitler
            final_score = min(final_score, -65.0)
            msg = "🚨 SİSTEMİK KRİZ / LİKİDİTE ŞOKU (Net-Short / Agresif Satış Kilitlendi)"
            css = "div-short-lock"
            action = "🩸 AGRESİF SHORT / HEDGE: Makro anomali patlaması nedeniyle LONG kapalı, Vadeli Short pozisyon koru."
            badge_cls = "action-badge-bear"
        elif final_score > 18.0:
            msg = "🚀 BOĞA İVMESİ (4H Pozisyon Yönü: LONG)"
            css = "div-bull"
            action = "🚀 LONG POZİSYON TAŞI: Mikro ve Makro ivme uyumlu. Düzeltmelerde alım yönlü bak."
            badge_cls = "action-badge"
        elif final_score < -18.0:
            msg = "🩸 AYI BASKISI (4H Pozisyon Yönü: SHORT)"
            css = "div-bear"
            action = "🩸 SHORT POZİSYON TAŞI: Ayı vektörü baskın. Direnç seviyelerinden satış kurgula."
            badge_cls = "action-badge-bear"
        else:
            msg = "⚪ DENGELİ KONSOLİDASYON (Piyasa Yönsüz / Bekle-Gör)"
            css = "div-neutral"
            action = "🛑 YÖNSÜZ PİYASA: Net kırılım (+18 veya -18) gelmeden yeni pozisyon açma."
            badge_cls = "action-badge-neutral"

        top_pos = breakdown_df.iloc[0] if not breakdown_df.empty else None
        top_neg = breakdown_df.iloc[-1] if not breakdown_df.empty else None
        pos_str = f"{top_pos['Faktör Katmanı']} ({top_pos['Katkı']:.2f})" if top_pos is not None else "-"
        neg_str = f"{top_neg['Faktör Katmanı']} ({top_neg['Katkı']:.2f})" if top_neg is not None else "-"

        commentary = {
            'structure': f"En güçlü destekleyici faktör: **{pos_str}** | En güçlü baskılayıcı faktör: **{neg_str}**",
            'action': action,
            'badge_cls': badge_cls
        }

        return {'score': final_score, 'table': breakdown_df, 'msg': msg, 'css': css, 'commentary': commentary}

    def compute_all_assets(self, df):
        stresses = self.evaluate_system_stresses(df)
        
        # BÜTÜN FAKTÖRLERİN Z-SKORLARI
        spx_z = self.compute_rolling_z(df['SPX'])
        nq_z = self.compute_rolling_z(df['NQ'])
        xau_z = self.compute_rolling_z(df['XAU'])
        xag_z = self.compute_rolling_z(df['XAG'])
        btc_z = self.compute_rolling_z(df['BTC'])
        
        copper_gold_z = self.compute_ratio_z(df['COPPER'], df['XAU'])
        gold_oil_z = self.compute_ratio_z(df['XAU'], df['OIL'])
        slv_gld_z = self.compute_ratio_z(df['XAG'], df['XAU'])
        xme_gld_z = self.compute_ratio_z(df['XME'], df['XAU'])
        eth_btc_z = self.compute_ratio_z(df['ETH'], df['BTC'])

        # GÜMÜŞ (XAG) FAKTÖR MATRİSİ (Ters Korelasyonlar '-1' İşaretli)
        xag_matrix = {
            'XAG_Pure_Momentum': {'val': xag_z, 'dir': 1.0, 'weight': 2.5},
            'Copper_Gold_Ratio (Sanayi Talebi)': {'val': copper_gold_z, 'dir': 1.0, 'weight': 2.0},
            'SLV_GLD_Relative_Beta': {'val': slv_gld_z, 'dir': 1.0, 'weight': 1.5},
            'XME_Madencilik_İvmesi': {'val': xme_gld_z, 'dir': 1.0, 'weight': 1.2},
            'Real_Yield_Shock (Reel Faiz Baskısı)': {'val': stresses['yield_shock'], 'dir': -1.0, 'weight': 1.8}, # TERS
            'DXY_Pressure (Dolar Gücü Baskısı)': {'val': stresses['dxy_shock'], 'dir': -1.0, 'weight': 1.5},      # TERS
            'Credit_Risk_Spread': {'val': stresses['credit_stress'], 'dir': -1.0, 'weight': 1.0}                  # TERS
        }

        # ALTIN (XAU) FAKTÖR MATRİSİ
        xau_matrix = {
            'XAU_Pure_Momentum': {'val': xau_z, 'dir': 1.0, 'weight': 2.5},
            'Real_Yield_Shock (Reel Faiz Baskısı)': {'val': stresses['yield_shock'], 'dir': -1.0, 'weight': 2.5}, # TERS
            'DXY_Pressure (Dolar Gücü Baskısı)': {'val': stresses['dxy_shock'], 'dir': -1.0, 'weight': 2.0},      # TERS
            'Gold_Oil_Monetary_Ratio': {'val': gold_oil_z, 'dir': 1.0, 'weight': 1.2},
            'Credit_Systemic_Stress': {'val': stresses['credit_stress'], 'dir': 1.0, 'weight': 1.5} # Krizde Altına kaçış (+)
        }

        # SPX FAKTÖR MATRİSİ
        spx_matrix = {
            'SPX_Pure_Momentum': {'val': spx_z, 'dir': 1.0, 'weight': 2.5},
            'Funding_Liquidity_Stress': {'val': stresses['funding_stress'], 'dir': -1.0, 'weight': 2.2}, # TERS
            'Credit_Risk_Spread': {'val': stresses['credit_stress'], 'dir': -1.0, 'weight': 2.0},        # TERS
            'Copper_Gold_Growth_Proxy': {'val': copper_gold_z, 'dir': 1.0, 'weight': 1.2},
            'DXY_Pressure': {'val': stresses['dxy_shock'], 'dir': -1.0, 'weight': 1.0}                   # TERS
        }

        # NASDAQ (NQ) FAKTÖR MATRİSİ
        nq_matrix = {
            'NQ_Pure_Momentum': {'val': nq_z, 'dir': 1.0, 'weight': 2.5},
            'Yield_Shock (Faiz Baskısı)': {'val': stresses['yield_shock'], 'dir': -1.0, 'weight': 2.2},  # TERS
            'Funding_Liquidity_Stress': {'val': stresses['funding_stress'], 'dir': -1.0, 'weight': 2.0},# TERS
            'Credit_Risk_Spread': {'val': stresses['credit_stress'], 'dir': -1.0, 'weight': 1.5}        # TERS
        }

        # KRİPTO (BTC/ETH) FAKTÖR MATRİSİ
        crypto_matrix = {
            'BTC_Pure_Momentum': {'val': btc_z, 'dir': 1.0, 'weight': 2.5},
            'ETH_BTC_Beta_Leverage': {'val': eth_btc_z, 'dir': 1.0, 'weight': 1.5},
            'Funding_Liquidity_Stress': {'val': stresses['funding_stress'], 'dir': -1.0, 'weight': 2.2},# TERS
            'DXY_Pressure': {'val': stresses['dxy_shock'], 'dir': -1.0, 'weight': 1.5}                  # TERS
        }

        results = {
            'XAG': self.process_asset_analysis(df, 'XAG', xag_matrix, stresses),
            'XAU': self.process_asset_analysis(df, 'XAU', xau_matrix, stresses),
            'SPX': self.process_asset_analysis(df, 'SPX', spx_matrix, stresses),
            'NQ':  self.process_asset_analysis(df, 'NQ', nq_matrix, stresses),
            'CRYPTO': self.process_asset_analysis(df, 'CRYPTO', crypto_matrix, stresses)
        }

        # REJİM MİMARİSİ
        if stresses['is_crisis']:
            regime = {
                'name': "🚨 SİSTEMİK LİKİDİTE KRİZİ & ANOMALİ ALARMI",
                'css': "regime-crisis",
                'desc': "Kredi spreadleri veya likidite stresi Z > 2.0 eşiğini aştı. Tüm riskli varlıklarda Short yönlü koruma aktif."
            }
        elif stresses['copper_gold'] if 'copper_gold' in stresses else copper_gold_z > 0.8:
            regime = {
                'name': "🚀 REFLASYON VE BÜYÜME GENİŞLEMESİ",
                'css': "regime-bull",
                'desc': "Sanayi emtiası ve küresel büyüme dinamikleri güçlü alıcılı."
            }
        elif stresses['credit_stress'] > 1.0 or stresses['yield_shock'] > 1.0:
            regime = {
                'name': "🩸 SIKI PARA POLİTİKASI VE FAİZ BASKISI",
                'css': "regime-bear",
                'desc': "Yükselen faizler ve daralan kredi muslukları değerlemeleri baskılıyor."
            }
        else:
            regime = {
                'name': "⚪ ADAPTİF DENGELİ PİYASA REJİMİ",
                'css': "regime-mixed",
                'desc': "Çok değişkenli makro stres nötr bantta. Varlık bazlı mikro ayrışmalar ön planda."
            }

        return results, regime

# ==========================================
# 3. DASHBOARD VE ARAYÜZ
# ==========================================
engine = FullyAdaptiveQuantEngine()

st.title("🏛️ TIER-1 ADAPTIVE QUANT TERMINAL (v150.3-PRO)")
st.caption("Rolling Z-Score | Dinamik Ters Korelasyon Matrisi | Anomali ve Short Kilit Sistemli Engine")

try:
    df_grid = engine.fetch_synchronized_grid()
    
    if df_grid.empty or len(df_grid) < 10:
        st.warning("Veri havuzu senkronize ediliyor...")
    else:
        results, regime_info = engine.compute_all_assets(df_grid)

        st.markdown(f"""
        <div class="regime-box {regime_info['css']}">
            Mevcut Makro Rejim: {regime_info['name']}<br>
            <span style="font-size:11px; font-weight:normal; opacity:0.85;">{regime_info['desc']}</span>
        </div>
        """, unsafe_allow_html=True)

        tab_spx, tab_nq, tab_xau, tab_xag, tab_crypto = st.tabs([
            "S&P 500 (ES=F)", "NASDAQ (NQ=F)", "ALTIN (GC=F)", "GÜMÜŞ (SI=F)", "KRİPTO (BTC+ETH)"
        ])

        def render_adaptive_tab(res, title):
            score = res['score']
            table = res['table']
            div_msg = res['msg']
            div_class = res['css']
            commentary = res['commentary']

            col1, col2 = st.columns([1, 2])
            with col1:
                st.markdown(f"### {title} Adaptif Rotası")
                c = "#00E676" if score > 18 else ("#FF1744" if score < -18 else "#ECEFF1")
                if "SHORT" in div_msg:
                    c = "#FF5252"

                st.markdown(f"<h1 style='color: {c}; font-size: 55px; margin:0;'>{score:.1f}</h1>", unsafe_allow_html=True)
                st.markdown(f'<div class="{div_class}">{div_msg}</div>', unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="commentary-card">
                    <div class="commentary-header">📊 Matris Teşhisi:</div>
                    <div>{commentary['structure']}</div>
                    <div class="{commentary['badge_cls']}">{commentary['action']}</div>
                </div>
                """, unsafe_allow_html=True)

            with col2:
                if not table.empty:
                    fig = go.Figure(go.Bar(
                        x=table['Katkı'], y=table['Faktör Katmanı'], orientation='h',
                        marker_color=np.where(table['Katkı'] > 0, '#00E676', '#FF1744')
                    ))
                    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=250, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
                    st.plotly_chart(fig, use_container_width=True)

            st.dataframe(table, use_container_width=True, hide_index=True)

        with tab_spx:
            render_adaptive_tab(results.get('SPX'), "S&P 500 (ES=F)")

        with tab_nq:
            render_adaptive_tab(results.get('NQ'), "NASDAQ (NQ=F)")

        with tab_xau:
            render_adaptive_tab(results.get('XAU'), "ALTIN (GC=F)")

        with tab_xag:
            render_adaptive_tab(results.get('XAG'), "GÜMÜŞ (SI=F)")

        with tab_crypto:
            render_adaptive_tab(results.get('CRYPTO'), "KRİPTO (BTC+ETH)")

except Exception as e:
    st.error(f"Sistem Hatası: {str(e)}")
