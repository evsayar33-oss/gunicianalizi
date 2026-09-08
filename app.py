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
# 1. TERMINAL YAPILANDIRMASI
# ==========================================
st.set_page_config(page_title="TIER-1 ADAPTIVE QUANT TERMINAL (v300-FINAL)", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; color: #E0E6ED; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    h1 { font-family: 'Courier New', monospace; font-size: 20px; }
    h2, h3 { color: #ECEFF1; font-size: 14px; }
    .regime-card { padding: 12px 18px; border-radius: 6px; font-weight: bold; font-size: 13px; margin-bottom: 15px; border-left: 6px solid; }
    .regime-bull { background-color: #002B22; color: #00E676; border-color: #00E676; }
    .regime-bear { background-color: #330000; color: #FF1744; border-color: #FF1744; }
    .regime-crisis { background-color: #4A0000; color: #FF5252; border-color: #FF1744; animation: blink 1.5s infinite; }
    .regime-neutral { background-color: #262000; color: #FFB300; border-color: #FFB300; }
    .badge-lock { background-color: #B71C1C; color: #FFFFFF; padding: 5px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-bull { background-color: #004D40; color: #00E676; padding: 5px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-bear { background-color: #4A148C; color: #FF1744; padding: 5px 10px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .action-box { background-color: #121824; border: 1px solid #2A364F; border-radius: 6px; padding: 10px; margin-top: 10px; font-size: 12px; }
    </style>
    """, unsafe_allow_html=True)

st_autorefresh(interval=60000, limit=None, key="quant_final_refresh")

# ==========================================
# 2. BULUT KORUMALI VERİ MOTORU (GEO-BLOCK FALLBACK)
# ==========================================
class ResilientDataEngine:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    def fetch_yahoo_series(self, symbol):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=7d&interval=15m"
        try:
            r = requests.get(url, headers=self.headers, timeout=4)
            if r.status_code == 200:
                res = r.json()['chart']['result'][0]
                timestamps = pd.to_datetime(res['timestamp'], unit='s')
                quotes = res['indicators']['quote'][0]
                df = pd.DataFrame({
                    'Close': quotes.get('close'),
                    'Volume': quotes.get('volume', [1]*len(timestamps)),
                    'High': quotes.get('high'),
                    'Low': quotes.get('low')
                }, index=timestamps).dropna()
                return df
        except Exception:
            pass
        return pd.DataFrame()

    def fetch_all_market_grid(self):
        symbols = {
            'SPX': 'ES=F', 'NQ': 'NQ=F', 'XAU': 'GC=F', 'XAG': 'SI=F',
            'COPPER': 'HG=F', 'OIL': 'CL=F', 'EUR': 'EURUSD=X', 'JPY': 'USDJPY=X',
            'BTC': 'BTC-USD', 'ETH': 'ETH-USD', 'TNX': '^TNX', 'VIX': '^VIX',
            'HYG': 'HYG', 'LQD': 'LQD', 'XME': 'XME'
        }
        grid = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {sym: executor.submit(self.fetch_yahoo_series, ticker) for sym, ticker in symbols.items()}
            for sym, future in futures.items():
                df = future.result()
                if not df.empty:
                    grid[sym] = df

        return grid

    def get_binance_taker_ratio_with_fallback(self, btc_df):
        # Binance API denenir, Streamlit Cloud AWS engeline takılırsa Yahoo Volume Delta Proxy devreye girer
        try:
            url = "https://fapi.binance.com/futures/data/takerlongshortRatio?symbol=BTCUSDT&period=15m&limit=30"
            r = requests.get(url, headers=self.headers, timeout=2)
            if r.status_code == 200:
                data = r.json()
                series = pd.Series([float(x['buySellRatio']) for x in data])
                return series.iloc[-1], series
        except Exception:
            pass

        # FALLBACK: Binance engellendiyse BTC High/Low/Volume üzerinden Taker Proxy üretilir
        if not btc_df.empty:
            buy_volume_proxy = btc_df['Volume'] * ((btc_df['Close'] - btc_df['Low']) / (btc_df['High'] - btc_df['Low'] + 1e-6))
            sell_volume_proxy = btc_df['Volume'] - buy_volume_proxy
            ratio_series = (buy_volume_proxy / (sell_volume_proxy + 1e-6)).replace([np.inf, -np.inf], 1.0)
            return float(ratio_series.iloc[-1]), ratio_series
        
        return 1.0, pd.Series([1.0]*20)

# ==========================================
# 3. CANLI Z-SCORE VE ANOMALİ MOTORU
# ==========================================
class RobustQuantProcessor:
    def compute_z_score(self, series, window=24):
        if series is None or len(series) < 5:
            return 0.0
        if isinstance(series, pd.DataFrame):
            series = series['Close']
        
        pct = series.pct_change().dropna()
        if len(pct) < 5:
            return 0.0
        
        mean = pct.rolling(window=window, min_periods=3).mean()
        std = pct.rolling(window=window, min_periods=3).std().replace(0, 1e-6)
        z = (pct - mean) / std
        val = z.iloc[-1]
        return float(np.clip(val, -3.5, 3.5)) if not np.isnan(val) else 0.0

    def compute_ratio_z(self, df1, df2, window=24):
        if df1.empty or df2.empty:
            return 0.0
        s1 = df1['Close']
        s2 = df2['Close']
        idx = s1.index.intersection(s2.index)
        if len(idx) < 5:
            return 0.0
        ratio = s1.loc[idx] / (s2.loc[idx] + 1e-6)
        return self.compute_z_score(ratio, window)

    def sigmoid_smooth(self, z, k=1.5):
        return float(np.tanh(z / k))

    def evaluate(self, grid, binance_taker_tuple):
        taker_val, taker_series = binance_taker_tuple
        
        # MAKRO STRES METRİKLERİ
        hyg_df = grid.get('HYG', pd.DataFrame())
        lqd_df = grid.get('LQD', pd.DataFrame())
        vix_df = grid.get('VIX', pd.DataFrame())
        tnx_df = grid.get('TNX', pd.DataFrame())
        eur_df = grid.get('EUR', pd.DataFrame())

        credit_stress_z = -self.compute_ratio_z(hyg_df, lqd_df) if not hyg_df.empty and not lqd_df.empty else 0.0
        vix_z = self.compute_z_score(vix_df)
        yield_z = self.compute_z_score(tnx_df)
        dxy_z = -self.compute_z_score(eur_df)

        anomali_score = float(np.linalg.norm([credit_stress_z, vix_z, yield_z, dxy_z]) / 2.0)
        is_crisis = anomali_score > 1.75 or vix_z > 2.0 or credit_stress_z > 2.0

        # HER VARLIĞIN ÖZGÜN FAKTÖR MATRİSİ
        def run_matrix(factor_dict, is_crisis_flag, asset_key):
            tot_s, tot_w = 0.0, 0.0
            rows = []
            for name, f in factor_dict.items():
                z = f['z']
                direction = f['dir']
                base_w = f['w']
                
                eff = self.sigmoid_smooth(z) * direction
                w = base_w * (2.2 if is_crisis_flag and direction < 0 else 1.0)
                contrib = eff * w
                
                tot_s += contrib
                tot_w += w
                rows.append({
                    'Gösterge Katmanı': name,
                    'Z-Score': round(z, 2),
                    'Korelasyon Yönü': 'Doğrudan (+)' if direction > 0 else 'Ters (-)',
                    'Net Katkı': round(contrib, 3)
                })
            
            final = (tot_s / (tot_w + 1e-6)) * 100.0
            if is_crisis_flag and asset_key in ['SPX', 'NQ', 'CRYPTO', 'XAG']:
                final = min(final, -65.0) # SHORT KİLİTLENMESİ

            return float(np.clip(final, -100.0, 100.0)), pd.DataFrame(rows).sort_values('Net Katkı', ascending=False)

        # 1. SPX
        spx_factors = {
            'SPX Pure Momentum': {'z': self.compute_z_score(grid.get('SPX')), 'dir': 1.0, 'w': 2.5},
            'Credit Risk Spread (HYG/LQD)': {'z': credit_stress_z, 'dir': -1.0, 'w': 2.0},
            'VIX Volatility Strain': {'z': vix_z, 'dir': -1.0, 'w': 1.8},
            'Copper/Gold Growth Ratio': {'z': self.compute_ratio_z(grid.get('COPPER', pd.DataFrame()), grid.get('XAU', pd.DataFrame())), 'dir': 1.0, 'w': 1.2}
        }
        spx_score, spx_df = run_matrix(spx_factors, is_crisis, 'SPX')

        # 2. NQ
        nq_factors = {
            'NQ Pure Momentum': {'z': self.compute_z_score(grid.get('NQ')), 'dir': 1.0, 'w': 2.5},
            '10Y Yield Pressure (TNX)': {'z': yield_z, 'dir': -1.0, 'w': 2.2},
            'Credit Risk Spread': {'z': credit_stress_z, 'dir': -1.0, 'w': 1.8},
            'DXY Currency Strain': {'z': dxy_z, 'dir': -1.0, 'w': 1.2}
        }
        nq_score, nq_df = run_matrix(nq_factors, is_crisis, 'NQ')

        # 3. ALTIN (XAU)
        xau_factors = {
            'XAU Pure Momentum': {'z': self.compute_z_score(grid.get('XAU')), 'dir': 1.0, 'w': 2.5},
            '10Y Yield Pressure': {'z': yield_z, 'dir': -1.0, 'w': 2.2},
            'DXY Currency Strain': {'z': dxy_z, 'dir': -1.0, 'w': 2.0},
            'Systemic Risk Hedge Demand': {'z': credit_stress_z, 'dir': 1.0, 'w': 1.5}
        }
        xau_score, xau_df = run_matrix(xau_factors, is_crisis, 'XAU')

        # 4. GÜMÜŞ (XAG)
        xag_factors = {
            'XAG Pure Momentum': {'z': self.compute_z_score(grid.get('XAG')), 'dir': 1.0, 'w': 2.5},
            'Copper/Gold Ratio (Sanayi Talebi)': {'z': self.compute_ratio_z(grid.get('COPPER', pd.DataFrame()), grid.get('XAU', pd.DataFrame())), 'dir': 1.0, 'w': 2.2},
            'XME Mining Equity Beta': {'z': self.compute_z_score(grid.get('XME')), 'dir': 1.0, 'w': 1.5},
            '10Y Yield Pressure': {'z': yield_z, 'dir': -1.0, 'w': 1.8},
            'DXY Currency Strain': {'z': dxy_z, 'dir': -1.0, 'w': 1.5}
        }
        xag_score, xag_df = run_matrix(xag_factors, is_crisis, 'XAG')

        # 5. KRİPTO (BTC/ETH)
        crypto_factors = {
            'Binance Taker Buy/Sell Volume Ratio': {'z': self.compute_z_score(taker_series), 'dir': 1.0, 'w': 3.0},
            'BTC Pure Momentum': {'z': self.compute_z_score(grid.get('BTC')), 'dir': 1.0, 'w': 2.0},
            'ETH/BTC Beta Ratio': {'z': self.compute_ratio_z(grid.get('ETH', pd.DataFrame()), grid.get('BTC', pd.DataFrame())), 'dir': 1.0, 'w': 1.5},
            'Credit Risk Spread': {'z': credit_stress_z, 'dir': -1.0, 'w': 1.8},
            'DXY Currency Strain': {'z': dxy_z, 'dir': -1.0, 'w': 1.5}
        }
        crypto_score, crypto_df = run_matrix(crypto_factors, is_crisis, 'CRYPTO')

        return {
            'is_crisis': is_crisis,
            'anomali_score': anomali_score,
            'taker_val': taker_val,
            'assets': {
                'SPX': {'score': spx_score, 'df': spx_df},
                'NQ': {'score': nq_score, 'df': nq_df},
                'XAU': {'score': xau_score, 'df': xau_df},
                'XAG': {'score': xag_score, 'df': xag_df},
                'CRYPTO': {'score': crypto_score, 'df': crypto_df}
            }
        }

# ==========================================
# 4. ARAYÜZ VE TABS
# ==========================================
data_engine = ResilientDataEngine()
processor = RobustQuantProcessor()

st.title("🏛️ TIER-1 MULTI-ASSET QUANT TERMINAL (v300-FINAL)")

try:
    with st.spinner("Canlı Piyasa ve Emir Akış Verileri Senkronize Ediliyor..."):
        grid = data_engine.fetch_all_market_grid()
        btc_df = grid.get('BTC', pd.DataFrame())
        taker_tuple = data_engine.get_binance_taker_ratio_with_fallback(btc_df)
        calc = processor.evaluate(grid, taker_tuple)

    if calc['is_crisis']:
        st.markdown(f"""
        <div class="regime-card regime-crisis">
            🚨 KRİZ / SİSTEMİK ANOMALİ ALARMI (Anomali Skoru: {calc['anomali_score']:.2f})<br>
            <span style="font-weight:normal; font-size:11px;">Volatilite veya Kredi spreadleri kritik Z-Eşiğini aştı. Tüm riskli varlıklarda Short Kilit aktif.</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="regime-card regime-bull">
            🌐 DİNAMİK DENGELİ MAKRO REJİM (Anomali Skoru: {calc['anomali_score']:.2f})<br>
            <span style="font-weight:normal; font-size:11px;">Canlı Taker Buy/Sell Volume Ratio Proxy: {calc['taker_val']:.3f} | Sistemik Risk Nötr.</span>
        </div>
        """, unsafe_allow_html=True)

    # 5 VARLIĞIN TAMAMI EKLENDİ
    t_spx, t_nq, t_xau, t_xag, t_crypto = st.tabs([
        "S&P 500 (SPX)", "NASDAQ (NQ)", "ALTIN (XAU)", "GÜMÜŞ (XAG)", "KRİPTO (BTC/ETH)"
    ])

    def render_tab_content(asset_key, title):
        data = calc['assets'][asset_key]
        score = data['score']
        df = data['df']

        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown(f"### {title} Yön Skoru")
            col_code = "#00E676" if score > 18 else ("#FF1744" if score < -18 else "#FFB300")
            if score <= -65: col_code = "#B71C1C"
            st.markdown(f"<h1 style='color: {col_code}; font-size: 55px; margin:0;'>{score:.1f}</h1>", unsafe_allow_html=True)
            
            if score <= -65:
                st.markdown('<span class="badge-lock">🚨 SHORT KİLİTLENDİ (ANOMALİ)</span>', unsafe_allow_html=True)
            elif score > 18:
                st.markdown('<span class="badge-bull">🚀 LONG POZİSYON TAŞI</span>', unsafe_allow_html=True)
            elif score < -18:
                st.markdown('<span class="badge-bear">🩸 SHORT / SATIŞ BASKISI</span>', unsafe_allow_html=True)
            else:
                st.markdown('<span class="badge-bear" style="background:#262000; color:#FFB300;">⚪ NÖTR / DENGELİ</span>', unsafe_allow_html=True)

        with c2:
            if not df.empty:
                fig = go.Figure(go.Bar(
                    x=df['Net Katkı'], y=df['Gösterge Katmanı'], orientation='h',
                    marker_color=np.where(df['Net Katkı'] > 0, '#00E676', '#FF1744')
                ))
                fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=200, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#CFD8DC', size=10))
                st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df, use_container_width=True, hide_index=True)

    with t_spx: render_tab_content('SPX', 'S&P 500')
    with t_nq: render_tab_content('NQ', 'NASDAQ')
    with t_xau: render_tab_content('XAU', 'ALTIN')
    with t_xag: render_tab_content('XAG', 'GÜMÜŞ')
    with t_crypto: render_tab_content('CRYPTO', 'KRİPTO')

except Exception as e:
    st.error(f"Hesaplama / Veri Hatası: {str(e)}")
