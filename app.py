# app.py - FINAL VERSION FOR DEPLOYMENT (No sidebar API input)
"""
Veritas AI - Fake News Detection System
- No sidebar API input (uses secrets or .env)
- History (last 5) shown under analyze button
- PDF always available for current analysis
"""

import os
import re
import json
from typing import Dict, Optional
from datetime import datetime

import streamlit as st
from dotenv import load_dotenv
from groq import Groq
from fpdf import FPDF

# Load local .env file (safe for local development)
load_dotenv()

# Helper to get API key from Streamlit secrets (cloud) or environment (local)
def get_api_key() -> Optional[str]:
    try:
        # Deployed on Streamlit Cloud: use secrets.toml
        return st.secrets["GROQ_API_KEY"]
    except Exception:
        # Local development: use .env file
        return os.getenv("GROQ_API_KEY")

st.set_page_config(
    page_title="Veritas AI | Truth Detection",
    page_icon="✅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CSS ====================
def apply_css():
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #FFF5E6 0%, #FFE4CC 100%); }
    .card { background: rgba(255,255,255,0.95); border-radius: 20px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
    .badge-real { background: #10B981; color: white; padding: 0.5rem 1.5rem; border-radius: 40px; display: inline-block; font-weight: 700; font-size: 1.2rem; }
    .badge-fake { background: #EF4444; color: white; padding: 0.5rem 1.5rem; border-radius: 40px; display: inline-block; font-weight: 700; font-size: 1.2rem; }
    .stButton>button { background: linear-gradient(135deg, #FF8C00, #FF6B00) !important; color: white !important; border-radius: 40px !important; font-weight: 600 !important; }
    .analysis-box { background: #F8F9FA; border-radius: 16px; padding: 1rem; margin: 0.5rem 0; border-left: 6px solid #FF8C00; }
    .history-item { background: white; border-radius: 12px; padding: 0.75rem; margin-bottom: 0.5rem; border-left: 4px solid #FF8C00; transition: 0.2s; }
    .history-item:hover { transform: translateX(4px); box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    .indicator { background: #FFF3E0; border-radius: 20px; padding: 0.2rem 0.8rem; margin: 0.2rem; display: inline-block; font-size: 0.85rem; }
    </style>
    """, unsafe_allow_html=True)

# ==================== SESSION ====================
def init_session():
    if 'history' not in st.session_state:
        st.session_state.history = []
    if 'current_text' not in st.session_state:
        st.session_state.current_text = ""
    if 'current_analysis' not in st.session_state:
        st.session_state.current_analysis = None

# ==================== GROQ ANALYSIS ====================
def analyze_text(news_text: str, api_key: str) -> Dict:
    if not api_key or not api_key.startswith('gsk_'):
        return {'prediction': 'ERROR', 'confidence': 0, 'reasoning': 'Invalid API key', 'key_indicators': []}
    
    try:
        client = Groq(api_key=api_key)
        prompt = f"""Analyze if this news is REAL or FAKE. Respond JSON only.

News: "{news_text[:1500]}"

Output format:
{{"prediction":"REAL or FAKE","confidence":50,"reasoning":"2-3 sentence analysis","key_indicators":["indicator1","indicator2"]}}"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a fake news expert. Reply with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        raw = response.choices[0].message.content.strip()
        if raw.startswith('```'):
            raw = re.sub(r'^```\w*\n?', '', raw)
            raw = re.sub(r'\n?```$', '', raw)
        
        data = json.loads(raw)
        return {
            'prediction': data.get('prediction', 'UNKNOWN'),
            'confidence': float(data.get('confidence', 50)),
            'reasoning': data.get('reasoning', 'No reasoning'),
            'key_indicators': data.get('key_indicators', [])
        }
    except Exception as e:
        return {'prediction': 'ERROR', 'confidence': 0, 'reasoning': str(e), 'key_indicators': []}

# ==================== PDF GENERATION ====================
def make_pdf(analysis: Dict, original_text: str) -> bytes:
    """Generate PDF report - unchanged from working version"""
    from fpdf import FPDF
    import re
    from datetime import datetime
    
    def clean_text_simple(text):
        """Remove all problematic characters"""
        if not text or text == "None":
            return "Information not available"
        
        text = str(text)
        replacements = {
            '•': '-', '…': '...', '—': '-', '–': '-',
            '"': '"', '"': '"', ''': "'", ''': "'",
            '✓': 'OK', '❌': 'X', '⚠️': '!', '✅': 'YES',
            '🔍': 'Search', '📝': 'Note', '🧠': 'AI',
            '🔑': 'Key', '📎': 'Attachment', '🌟': '*',
            '😊': ':)', '😐': ':|', '😠': '>:[',
            '\u2022': '-', '\u2013': '-', '\u2014': '-',
            '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        text = text.encode('ascii', 'ignore').decode('ascii')
        text = re.sub(r'\s+', ' ', text)
        return text.strip()[:500]
    
    pdf = FPDF(unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
    
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(255, 140, 0)
    pdf.cell(170, 12, 'Veritas AI - Analysis Report', ln=True, align='C')
    
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(170, 8, f'Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', ln=True, align='C')
    pdf.ln(8)
    
    pdf.set_font('Helvetica', 'B', 14)
    pred = clean_text_simple(analysis.get('prediction', 'UNKNOWN'))
    pdf.cell(170, 10, f'Prediction: {pred}', ln=True)
    
    pdf.set_font('Helvetica', '', 11)
    confidence = analysis.get('confidence', 0)
    pdf.cell(170, 8, f'Confidence: {confidence:.1f}%', ln=True)
    pdf.ln(6)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(170, 8, 'EXECUTIVE SUMMARY', ln=True, fill=True)
    pdf.set_font('Helvetica', '', 10)
    explanation = clean_text_simple(analysis.get('explanation', 'No explanation available'))
    pdf.set_x(20)
    pdf.write(5, explanation)
    pdf.ln(8)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(170, 8, 'DETAILED ANALYSIS', ln=True, fill=True)
    pdf.set_font('Helvetica', '', 10)
    reasoning = clean_text_simple(analysis.get('reasoning', 'No detailed analysis available'))
    pdf.set_x(20)
    pdf.write(5, reasoning)
    pdf.ln(8)
    
    indicators = analysis.get('key_indicators', [])
    if indicators and len(indicators) > 0:
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(170, 8, 'KEY INDICATORS', ln=True, fill=True)
        pdf.set_font('Helvetica', '', 10)
        for i, indicator in enumerate(indicators[:5]):
            clean_ind = clean_text_simple(indicator)
            if clean_ind and len(clean_ind) > 1:
                pdf.set_x(25)
                pdf.cell(5, 6, '-', ln=0)
                pdf.set_x(30)
                pdf.write(5, clean_ind)
                pdf.ln(6)
        pdf.ln(4)
    
    if pdf.get_y() > 240:
        pdf.add_page()
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(170, 8, 'ORIGINAL TEXT PREVIEW', ln=True, fill=True)
    pdf.set_font('Helvetica', '', 9)
    preview = clean_text_simple(original_text[:600])
    pdf.set_x(20)
    pdf.write(4, preview)
    
    pdf.set_y(-15)
    pdf.set_font('Helvetica', 'I', 8)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(170, 5, 'Generated by Veritas AI - Fake News Detection System', ln=True, align='C')
    
    return bytes(pdf.output())

# ==================== MAIN APP ====================
def main():
    init_session()
    apply_css()
    
    # Get API key from secrets or environment
    api_key = get_api_key()
    
    # Sidebar (only test samples, no API input)
    with st.sidebar:
        st.markdown("## 📝 Test Samples")
        if st.button("📋 Load REAL News", use_container_width=True):
            st.session_state.current_text = "NASA's Perseverance rover collected 18 rock samples from Mars showing ancient water activity. NASA press release Jan 25, 2025."
            st.rerun()
        if st.button("📋 Load FAKE News", use_container_width=True):
            st.session_state.current_text = "BREAKING: Vaccines contain government tracking chips! WHO hiding proof! Share now!"
            st.rerun()
        st.markdown("---")
        st.markdown("### 💡 How to use")
        st.markdown("1. Paste news text in the main area\n2. Click 'Analyze Truth'\n3. Download PDF report")
    
    # Main area
    st.markdown("# Veritas AI")
    st.markdown("### AI-Powered News Authenticity Detection")
    st.markdown("---")
    
    col_left, col_right = st.columns([1, 1.2], gap="large")
    
    # LEFT COLUMN: Input + Analyze button + History
    with col_left:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 📝 Input News Text")
            
            news_text = st.text_area(
                "Paste news article here:",
                value=st.session_state.current_text,
                height=200,
                key="main_text",
                label_visibility="collapsed"
            )
            
            col_btn, col_clear = st.columns(2)
            with col_btn:
                analyze_clicked = st.button("🔍 Analyze Truth", type="primary", use_container_width=True)
            with col_clear:
                if st.button("🗑️ Clear", use_container_width=True):
                    st.session_state.current_text = ""
                    st.session_state.current_analysis = None
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        # History section (below analyze button)
        if st.session_state.history:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown("### 📜 Last 5 Analyses")
            for item in reversed(st.session_state.history[-5:]):
                badge = "✅ REAL" if item['prediction'] == "REAL" else "❌ FAKE"
                st.markdown(f"""
                <div class="history-item">
                    <div style="display: flex; justify-content: space-between;">
                        <strong>{badge}</strong>
                        <small style="color:#888;">{item['timestamp']}</small>
                    </div>
                    <div style="font-size: 0.85rem; color: #555;">{item['preview'][:80]}...</div>
                    <div style="font-size: 0.75rem; color: #FF8C00;">Confidence: {item['confidence']:.0f}%</div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    # RIGHT COLUMN: Results
    with col_right:
        if not api_key:
            st.error("❌ GROQ_API_KEY not found. Please set it in Streamlit Cloud secrets or local .env file.")
        elif analyze_clicked and news_text.strip():
            with st.spinner("Analyzing with AI..."):
                result = analyze_text(news_text, api_key)
                if result['prediction'] != 'ERROR':
                    # Save to history
                    st.session_state.history.append({
                        'prediction': result['prediction'],
                        'confidence': result['confidence'],
                        'preview': news_text[:80],
                        'timestamp': datetime.now().strftime("%H:%M:%S")
                    })
                    if len(st.session_state.history) > 5:
                        st.session_state.history.pop(0)
                    st.session_state.current_analysis = result
                    
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    if result['prediction'] == "REAL":
                        st.markdown('<div style="text-align:center"><span class="badge-real">✅ REAL - Legitimate News</span></div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div style="text-align:center"><span class="badge-fake">❌ FAKE - Misinformation Detected</span></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"### Confidence: {result['confidence']:.1f}%")
                    color = "#10B981" if result['confidence'] > 70 else "#F59E0B" if result['confidence'] > 40 else "#EF4444"
                    st.markdown(f'<div style="background:#E5E7EB; border-radius:20px; height:10px;"><div style="width:{result["confidence"]}%; background:{color}; height:10px; border-radius:20px;"></div></div>', unsafe_allow_html=True)
                    st.markdown("---")
                    
                    st.markdown("### 🧠 AI Analysis")
                    st.markdown(f'<div class="analysis-box">📌 <strong>Why this news is {result["prediction"]}:</strong><br><br>{result["reasoning"]}</div>', unsafe_allow_html=True)
                    
                    if result.get('key_indicators'):
                        st.markdown("### 🔍 Key Indicators")
                        indicators_html = "".join([f'<span class="indicator">⚠️ {ind}</span> ' for ind in result['key_indicators']])
                        st.markdown(f'<div>{indicators_html}</div>', unsafe_allow_html=True)
                    
                    if result['prediction'] == "FAKE":
                        st.info("💡 **Tip:** Look for sensational language, lack of sources, and urgent calls to share – common signs of misinformation.")
                    else:
                        st.success("💡 **Tip:** This content uses factual language, specific details, and credible references typical of legitimate journalism.")
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.markdown('<div class="card">', unsafe_allow_html=True)
                    try:
                        pdf_bytes = make_pdf(result, news_text)
                        st.download_button(
                            "📑 Download PDF Report",
                            pdf_bytes,
                            file_name=f"veritas_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"PDF error: {str(e)[:100]}")
                    st.markdown('</div>', unsafe_allow_html=True)
                else:
                    st.error(f"Analysis error: {result['reasoning']}")
        elif analyze_clicked and not news_text.strip():
            st.warning("⚠️ Please enter news text to analyze")
        else:
            # Show last analysis if exists (so PDF is always downloadable)
            if st.session_state.current_analysis:
                result = st.session_state.current_analysis
                st.markdown('<div class="card">', unsafe_allow_html=True)
                if result['prediction'] == "REAL":
                    st.markdown('<div style="text-align:center"><span class="badge-real">✅ REAL - Legitimate News</span></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div style="text-align:center"><span class="badge-fake">❌ FAKE - Misinformation Detected</span></div>', unsafe_allow_html=True)
                st.markdown(f"### Confidence: {result['confidence']:.1f}%")
                color = "#10B981" if result['confidence'] > 70 else "#F59E0B" if result['confidence'] > 40 else "#EF4444"
                st.markdown(f'<div style="background:#E5E7EB; border-radius:20px; height:10px;"><div style="width:{result["confidence"]}%; background:{color}; height:10px; border-radius:20px;"></div></div>', unsafe_allow_html=True)
                st.markdown("---")
                st.markdown("### 🧠 AI Analysis")
                st.markdown(f'<div class="analysis-box">{result["reasoning"]}</div>', unsafe_allow_html=True)
                if result.get('key_indicators'):
                    st.markdown("### 🔍 Key Indicators")
                    indicators_html = "".join([f'<span class="indicator">⚠️ {ind}</span> ' for ind in result['key_indicators']])
                    st.markdown(f'<div>{indicators_html}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('<div class="card">', unsafe_allow_html=True)
                try:
                    pdf_bytes = make_pdf(result, st.session_state.current_text or "No text saved")
                    st.download_button("📑 Download PDF Report", pdf_bytes, file_name=f"veritas_report.pdf", use_container_width=True)
                except Exception as e:
                    st.error(f"PDF error: {str(e)[:100]}")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="card" style="text-align:center;">', unsafe_allow_html=True)
                st.markdown("""
                <div style="font-size: 3rem;">🔍</div>
                <h3 style="color: #FF8C00;">Ready to Detect Misinformation</h3>
                <p>Paste news content on the left and click <strong>"Analyze Truth"</strong></p>
                <p style="font-size: 0.85rem; color:#888;">💡 Use the sidebar buttons to load sample news</p>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()