# app.py
import streamlit as st
import json
import os
import tempfile
from datetime import datetime
import time
import pandas as pd
import numpy as np
import io

# --- project modules ---
from src.agents.hs_code_agent import HSCodeAgent
from src.agents.fallback_analyzer import FallbackAnalyzer
# --- Guarded import (STEP 2) ---
try:
    from src.utils.report_generator import ReportGenerator
except ModuleNotFoundError:
    ReportGenerator = None

from src.utils.feedback_manager import FeedbackManager
from src.utils.analytics import AnalyticsEngine
from src.utils.duty_calculator import DutyCalculator
from src.utils.product_enhancer import ProductEnhancer
from src.utils.image_analyzer import ImageAnalyzer
from src.utils.enhanced_batch_processor import EnhancedBatchProcessor

# charts
import plotly.graph_objects as go
import plotly.express as px  # noqa: F401 (used inside AnalyticsEngine)

# =========================
# Page config
# =========================
st.set_page_config(
    page_title="HS Code Classifier",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# CSS
# =========================
st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: 700; color: #1f77b4; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.2rem; color: #666; margin-bottom: 2rem; }
    .metric-card { background: #f0f2f6; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0; }
    .confidence-high { color: #28a745; }
    .confidence-medium { color: #ffc107; }
    .confidence-low { color: #dc3545; }
    .stTabs [data-baseweb="tab-list"] { gap: 2rem; }
    .stTabs [data-baseweb="tab"] { padding: 1rem 2rem; }
</style>
""", unsafe_allow_html=True)

# =========================
# Helpers
# =========================
def _ensure_widget_defaults():
    for k in ["product_name_input", "origin_input", "material_input", "description_input", "use_input"]:
        if k not in st.session_state:
            st.session_state[k] = ""

def _apply_to_form_and_widgets(description: str = "", material: str = "", intended_use: str = "", product_name: str = ""):
    st.session_state.form_description = description or ""
    st.session_state.form_material = material or ""
    st.session_state.form_use = intended_use or ""
    if product_name is not None:
        st.session_state.product_name_input = product_name or st.session_state.get("product_name_input", "")
    st.session_state.description_input = st.session_state.form_description
    st.session_state.material_input = st.session_state.form_material
    st.session_state.use_input = st.session_state.form_use

def _schedule_fill(description: str, material: str, intended_use: str, product_name: str = ""):
    st.session_state.pending_fill = {
        "description": description or "",
        "material": material or "",
        "use": intended_use or "",
        "product_name": product_name or "",
    }

def clear_form():
    st.session_state.form_material = ""
    st.session_state.form_description = ""
    st.session_state.form_use = ""
    st.session_state.auto_filled_data = None
    st.session_state.image_analysis = {}   # dict, not None
    st.session_state.classification_complete = False
    st.session_state.product_name_input = ""
    st.session_state.origin_input = ""
    st.session_state.material_input = ""
    st.session_state.description_input = ""
    st.session_state.use_input = ""
    st.session_state.last_image_sig = None

# =========================
# Session state init
# =========================
if 'classification_history' not in st.session_state:
    st.session_state.classification_history = []

if 'agent' not in st.session_state:
    with st.spinner("Initializing AI components..."):
        try:
            st.session_state.agent = HSCodeAgent()
            st.session_state.fallback = FallbackAnalyzer()
            st.session_state.feedback_manager = FeedbackManager()
            st.session_state.calculator = DutyCalculator()
            st.session_state.enhancer = ProductEnhancer()
            st.session_state.image_analyzer = ImageAnalyzer()
            # Initialize batch processor
            st.session_state.batch_processor = EnhancedBatchProcessor(
                st.session_state.agent,
                st.session_state.fallback,
                st.session_state.calculator
            )
            st.session_state.init_success = True
        except Exception as e:
            st.error(f"Failed to initialize components: {str(e)}")
            st.session_state.init_success = False

st.session_state.setdefault('form_material', "")
st.session_state.setdefault('form_description', "")
st.session_state.setdefault('form_use', "")
st.session_state.setdefault('classification_complete', False)
st.session_state.setdefault('auto_filled_data', None)
st.session_state.setdefault('image_analysis', {})
st.session_state.setdefault('last_image_sig', None)
st.session_state.setdefault('enable_fallback', True)
st.session_state.setdefault('search_depth', 5)
_ensure_widget_defaults()

# =========================
# App
# =========================
def main():
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 1.5rem 0; background: linear-gradient(135deg, #1f77b4 0%, #2ca02c 100%); border-radius: 10px; margin-bottom: 1rem;'>
            <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>🌐</div>
            <div style='color: white; font-weight: bold; font-size: 1.2rem;'>HS CODE</div>
            <div style='color: #e0e0e0; font-size: 0.8rem;'>Classifier</div>
        </div>
        """, unsafe_allow_html=True)

        page = st.radio("Navigation",
                        ["🔍 Classifier", "📋 Batch Process", "💰 Duty Calculator", "📊 Analytics", "📚 About"],
                        label_visibility="collapsed")

        st.markdown("---")
        st.subheader("Quick Stats")
        if st.session_state.classification_history:
            st.metric("Classifications", len(st.session_state.classification_history))
            feedback_df = st.session_state.feedback_manager.get_all_feedback()
            if not feedback_df.empty:
                accuracy = st.session_state.feedback_manager.get_accuracy_stats()
                if accuracy:
                    st.metric("Accuracy", f"{accuracy['accuracy']:.1f}%")
        else:
            st.info("No classifications yet")

        if hasattr(st.session_state, 'enhancer'):
            st.markdown("---")
            st.caption(f"AI Model: {getattr(st.session_state.enhancer, 'model_name', 'Not initialized')}")

        st.markdown("---")
        st.caption("v1.0.0 | AI-Powered Classification")

    if not st.session_state.get('init_success', False):
        st.error("⚠️ System initialization failed. Please check your API keys and configuration.")
        st.stop()

    if page == "🔍 Classifier":
        show_classifier_page()
    elif page == "📋 Batch Process":
        show_batch_processing_page()
    elif page == "💰 Duty Calculator":
        show_duty_calculator_page()
    elif page == "📊 Analytics":
        show_analytics_page()
    elif page == "📚 About":
        show_about_page()

def show_classifier_page():
    if 'pending_fill' in st.session_state:
        pf = st.session_state.pending_fill
        _apply_to_form_and_widgets(
            pf.get("description", ""),
            pf.get("material", ""),
            pf.get("use", ""),
            pf.get("product_name", "")
        )
        del st.session_state.pending_fill

    st.markdown('<div class="main-header">📦 HS Code Classification System</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-powered customs classification for international trade</div>', unsafe_allow_html=True)

    if st.session_state.classification_complete:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.success("✅ Previous classification saved!")
            if st.button("🆕 Start New Classification", type="primary", use_container_width=True):
                clear_form()
                st.rerun()
        st.markdown("---")

    st.subheader("Product Information")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.text_input(
            "Product Name *",
            placeholder="e.g., LED desk lamp, Men's Cotton T-Shirt",
            help="Enter the product name - AI can auto-fill the rest",
            key="product_name_input"
        )
    with col2:
        st.write(""); st.write("")
        auto_fill_clicked = st.button(
            "🤖 Auto-Fill",
            type="secondary",
            use_container_width=True,
            key="auto_fill_btn",
            disabled=not st.session_state.product_name_input.strip()
        )

    if auto_fill_clicked:
        with st.spinner("🤖 AI is analyzing and generating detailed product information..."):
            try:
                enhanced_data = st.session_state.enhancer.enhance_product_info(st.session_state.product_name_input)
                if enhanced_data and enhanced_data.get('success', False):
                    desc = enhanced_data.get('description', '')
                    mat = enhanced_data.get('material', '')
                    use = enhanced_data.get('intended_use', '')
                    _schedule_fill(desc, mat, use, product_name=st.session_state.product_name_input)
                    st.session_state.auto_filled_data = enhanced_data
                    st.success(f"✨ Details auto-generated using {enhanced_data.get('model_used','AI')}!")
                    st.rerun()
                else:
                    error_msg = enhanced_data.get('error', 'Unknown error') if enhanced_data else 'No response from AI'
                    st.error(f"❌ Failed to auto-generate: {error_msg}")
                    with st.expander("🔧 Debug Information"):
                        st.json(enhanced_data if enhanced_data else {"error": "No response"})
                        st.info("Tips: Check your API key and internet connection")
            except Exception as e:
                st.error(f"❌ Exception occurred: {str(e)}")
                with st.expander("🔧 Full Error Details"):
                    import traceback
                    st.code(traceback.format_exc())

    if st.session_state.auto_filled_data and not st.session_state.classification_complete:
        model_info = st.session_state.auto_filled_data.get('model_used', '')
        if model_info:
            st.info(f"✨ Using AI Model: {model_info}")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input(
            "Material/Composition",
            placeholder="e.g., 100% Cotton, Stainless Steel",
            help="What is the product made of?",
            key="material_input",
        )
        st.text_input(
            "Country of Origin",
            placeholder="e.g., China, Bangladesh, Vietnam",
            help="Where is the product manufactured?",
            key="origin_input"
        )
    with col2:
        st.text_area(
            "Detailed Description *",
            placeholder="Enter product features, size, style, function...",
            height=100,
            help="Provide as much detail as possible. Use Auto-Fill for AI assistance!",
            key="description_input",
        )
        st.text_input(
            "Intended Use",
            placeholder="e.g., Office lighting, Casual wear",
            help="What is this product used for?",
            key="use_input",
        )

    if st.session_state.get('auto_filled_data') and not st.session_state.classification_complete:
        if st.button("🔄 Clear Auto-Fill", key="clear_autofill"):
            st.session_state.auto_filled_data = None
            _schedule_fill("", "", "", product_name=st.session_state.product_name_input)
            st.rerun()

    st.markdown("---")
    st.subheader("🖼️ Product Image Analysis (Optional)")

    uploaded_file = st.file_uploader(
        "Upload Product Image",
        type=["jpg", "jpeg", "png"],
        help="Upload a product image. The app will auto-fill product name & details."
    )

    if uploaded_file is not None:
      st.image(uploaded_file, caption="Uploaded Product Image", use_column_width=True)

    if uploaded_file is not None:
        try:
            file_bytes = uploaded_file.getvalue()
            image_sig = f"{uploaded_file.name}:{len(file_bytes)}"
        except Exception:
            image_sig = uploaded_file.name

        if st.session_state.get("last_image_sig") != image_sig:
            with st.spinner("🖼️ Auto-analyzing the product image..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                        tmp_file.write(file_bytes)
                        tmp_path = tmp_file.name

                    image_result = st.session_state.image_analyzer.analyze_product_image(tmp_path)
                    os.unlink(tmp_path)

                    if image_result.get("success"):
                        st.session_state.image_analysis = image_result
                        st.session_state.last_image_sig = image_sig

                        product_name_ai = image_result.get("product_name", "")
                        desc_ai        = image_result.get("description", "")
                        material_ai    = image_result.get("material", "")
                        use_ai         = image_result.get("intended_use", "")

                        _schedule_fill(
                            description=desc_ai,
                            material=material_ai,
                            intended_use=use_ai,
                            product_name=product_name_ai or st.session_state.product_name_input
                        )

                        st.session_state.auto_filled_data = {
                            "enhanced_name": product_name_ai,
                            "description": desc_ai,
                            "material": material_ai,
                            "intended_use": use_ai,
                            "model_used": "Image Analyzer (Gemini)",
                            "success": True,
                        }

                        st.info("✨ Auto-filled Product Name and details from the image.")
                        st.rerun()

                    else:
                        st.error(f"❌ Failed to analyze image: {image_result.get('error', 'Unknown error')}")
                except Exception as e:
                    st.error(f"❌ Image analysis error: {str(e)}")

    ia = st.session_state.get("image_analysis") or {}
    if ia.get("success"):
        ir = ia
        with st.expander("📋 Image Analysis Results", expanded=False):
            st.write(f"**Product Identified:** {ir.get('product_name', '')}")
            st.write(f"**Material:** {ir.get('material', '')}")
            st.write(f"**Construction:** {ir.get('construction', '')}")
            st.write(f"**Description:** {ir.get('description', '')}")
            if ir.get('features'):
                st.write(f"**Features:** {', '.join(ir['features'])}")
            st.write(f"**Intended Use:** {ir.get('intended_use', '')}")
            if ir.get('additional_notes'):
                st.write(f"**Notes:** {ir['additional_notes']}")

    st.markdown("---")
    with st.expander("⚙️ Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            st.slider("Search Depth", 3, 10, st.session_state.search_depth, key="search_depth")
        with col2:
            st.checkbox("Enable Fallback Analysis", value=st.session_state.enable_fallback, key="enable_fallback")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        classify_button = st.button("🔍 Classify Product", type="primary", use_container_width=True)

    if classify_button:
        product_name = st.session_state.product_name_input.strip()
        description  = st.session_state.description_input.strip()
        material     = st.session_state.material_input.strip()
        use_value    = st.session_state.use_input.strip()
        origin       = st.session_state.origin_input.strip()

        if not product_name or not description:
            st.error("⚠️ Please enter at least Product Name and Description")
        else:
            with st.spinner("🤖 Analyzing product and applying GRI rules..."):
                try:
                    product_info = {
                        'product_name': product_name,
                        'description': description,
                        'material': material,
                        'use': use_value,
                        'origin': origin
                    }

                    result = st.session_state.agent.classify_product(product_info) or {}

                    def _float_conf(x):
                        try:
                            s = str(x).strip()
                            s = s[:-1] if s.endswith("%") else s
                            n = float(s)
                            if 0.0 <= n <= 1.0:
                                n *= 100.0
                            return max(0.0, min(100.0, n))
                        except Exception:
                            return -1.0

                    rec_code = str(result.get('recommended_code', '')).strip().upper()
                    conf_val = _float_conf(result.get('confidence', -1))

                    missing_or_low = (rec_code in ("", "N/A", "ERROR")) or (conf_val < 50.0)

                    if st.session_state.enable_fallback and missing_or_low:
                        st.info("🔁 No strong DB match. Using LLM fallback…")
                        result = st.session_state.fallback.analyze_unknown_product(product_info)

                    if 'confidence' not in result:
                        result['confidence'] = f"{max(0.0, conf_val):.0f}%"
                    elif not str(result['confidence']).endswith("%"):
                        try:
                            result['confidence'] = f"{float(result['confidence']):.0f}%"
                        except Exception:
                            result['confidence'] = "0%"

                    result['timestamp'] = datetime.now().isoformat()
                    result['product_info'] = product_info
                    st.session_state.classification_history.append(result)
                    st.session_state.current_result = result
                    st.session_state.current_product_info = product_info
                    st.session_state.classification_complete = True

                    display_results(result, product_info)

                except Exception as e:
                    st.error(f"❌ Classification error: {str(e)}")
                    with st.expander("🔧 Error Details"):
                        import traceback
                        st.code(traceback.format_exc())

def display_results(result, product_info):
    st.success("✅ Classification Complete!")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🆕 New Classification", type="primary", use_container_width=True):
            clear_form()
            st.rerun()

    st.subheader("Recommended HS Code")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### HS Code")
        st.code(result.get('recommended_code', 'N/A'), language="text")
    with col2:
        st.markdown("### Duty Rate")
        st.metric("Rate", result.get('duty_rate', 'N/A'))
    with col3:
        st.markdown("### Confidence")
        confidence = result.get('confidence', '0%')
        try:
            confidence_val = float(str(confidence).replace('%', ''))
        except Exception:
            confidence_val = 0.0
        color_class = "confidence-high" if confidence_val >= 80 else ("confidence-medium" if confidence_val >= 60 else "confidence-low")
        st.markdown(f'<h3 class="{color_class}">{confidence_val:.0f}%</h3>', unsafe_allow_html=True)

    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=confidence_val, domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Confidence Score"},
        gauge={'axis': {'range': [None, 100]},
               'bar': {'color': "darkblue"},
               'steps': [{'range': [0, 60], 'color': "lightgray"},
                         {'range': [60, 80], 'color': "gray"},
                         {'range': [80, 100], 'color': "lightgreen"}],
               'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': 80}}
    ))
    fig.update_layout(height=250)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Classification Reasoning")
    st.write(result.get('reasoning', 'No reasoning provided'))

    if result.get('alternatives'):
        st.subheader("Alternative HS Codes")
        for alt in result['alternatives']:
            st.write(f"- `{alt}`")

    if result.get('hts_candidates'):
        with st.expander("📊 HTS Database Matches"):
            for i, candidate in enumerate(result['hts_candidates'], 1):
                st.markdown(f"**{i}. {candidate['hs_code']}** (Relevance: {candidate['relevance_score']:.2f})")
                st.write(f"Description: {candidate['description']}")
                st.write(f"Duty Rate: {candidate['duty_rate']}")
                st.divider()

    if result.get('cross_rulings'):
        with st.expander("📚 Relevant CROSS Rulings"):
            for ruling in result['cross_rulings']:
                st.markdown(f"**{ruling['ruling_number']}** - {ruling['date']}")
                st.write(f"HS Code: `{ruling['hs_code']}`")
                st.write(f"Summary: {ruling['description'][:200]}...")
                st.link_button("View Full Ruling", ruling['url'])
                st.divider()

    if result.get('needs_review'):
        st.warning("⚠️ **Low Confidence Detection**: This classification should be reviewed by a customs broker.")

    st.subheader("Export Classification Report")
    col1, col2 = st.columns(2)

    # JSON export works even without ReportLab
    with col1:
        if ReportGenerator is None:
            # build JSON manually (no PDF dependency)
            data = {"generated_at": datetime.now().isoformat(),
                    "product": product_info, "classification": result}
            json_report = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            rg = ReportGenerator()
            json_report = rg.generate_json_report(result, product_info)

        st.download_button(
            label="📥 Download JSON Report",
            data=json_report,
            file_name=f"hs_code_{product_info['product_name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            key="json_download"
        )

    # PDF export is shown only if ReportLab is installed
    with col2:
        if ReportGenerator is None:
            st.error("📄 PDF export disabled: install `reportlab` and redeploy.\n\n"
                     "Add `reportlab>=4.2.0` to requirements.txt.")
        else:
            try:
                rg = ReportGenerator()
                pdf_bytes = rg.generate_pdf_report(result, product_info)
                st.download_button(
                    label="📄 Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"hs_code_{product_info['product_name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    key="pdf_download"
                )
            except Exception as e:
                st.error(f"📄 PDF export failed: {e}")
                with st.expander("How to fix PDF export"):
                    st.write(
                        "Add Unicode TTF fonts (DejaVuSans.ttf and DejaVuSans-Bold.ttf) under "
                        "`src/utils/assets/fonts/`, then redeploy."
                    )

    st.markdown("---")
    display_feedback_section(result, product_info)

def display_feedback_section(result, product_info):
    st.subheader("📝 Help Us Improve")
    st.write("Your feedback helps improve classification accuracy for everyone!")

    col1, col2 = st.columns(2)
    with col1:
        was_correct = st.radio(
            "Was this classification correct?",
            options=[None, True, False],
            format_func=lambda x: "Select..." if x is None else ("✅ Yes, correct" if x else "❌ No, incorrect"),
            key="was_correct"
        )
    with col2:
        rating = st.select_slider("Rate this classification", options=[1, 2, 3, 4, 5], value=3, key="rating")
        st.caption("⭐" * rating)

    actual_code = None
    if was_correct is False:
        actual_code = st.text_input("What should the correct HS code be?",
                                    placeholder="e.g., 6203.42.40",
                                    help="If you know the correct code, please share it",
                                    key="actual_code")

    comments = st.text_area("Additional comments (optional)",
                            placeholder="Any other feedback about this classification...",
                            key="comments", height=100)

    if st.button("Submit Feedback", type="primary", key="submit_feedback"):
        if was_correct is None:
            st.warning("Please indicate if the classification was correct")
        else:
            user_feedback = {'rating': rating, 'was_correct': was_correct,
                             'actual_code': actual_code if actual_code else None,
                             'comments': comments}
            classification_data = {'product_info': product_info,
                                   'recommended_code': result.get('recommended_code'),
                                   'confidence': result.get('confidence'),
                                   'reasoning': result.get('reasoning')}
            feedback_id = st.session_state.feedback_manager.add_feedback(classification_data, user_feedback)
            st.success(f"✅ Thank you for your feedback! (ID: {feedback_id})")

def show_batch_processing_page():
    """Enhanced batch processing page with duty calculation"""
    
    st.markdown('<div class="main-header">📋 Batch Classification & Duty Calculator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Process multiple products and calculate duties at once</div>', unsafe_allow_html=True)
    
    processor = st.session_state.batch_processor
    
    # Tabs for different workflows
    tab1, tab2, tab3 = st.tabs(["📤 Upload & Process", "📊 Results & Duties", "📈 Duty Analysis"])
    
    with tab1:
        # Template section
        st.subheader("📥 Download Template")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            template_type = st.radio(
                "Template Type",
                ["Classification Only", "Classification + Duty Calculation"],
                horizontal=True,
                help="Choose template based on your needs"
            )
        
        with col2:
            include_duties = template_type == "Classification + Duty Calculation"
            template_csv = processor.create_template(include_duty_fields=include_duties)
            st.download_button(
                label="📄 Download CSV Template",
                data=template_csv,
                file_name=f"hs_classification_template_{'with_duties' if include_duties else 'basic'}.csv",
                mime="text/csv",
                type="primary"
            )
        
        with col3:
            st.info("💡 Use this template to ensure correct formatting")
        
        st.markdown("---")
        
        # File upload
        st.subheader("📤 Upload Products File")
        
        uploaded_file = st.file_uploader(
            "Choose a CSV or Excel file",
            type=['csv', 'xlsx', 'xls'],
            help="Required: product_name, description | Optional: material, origin, quantity, unit_value, customs_value"
        )
        
        if uploaded_file is not None:
            try:
                # Read file
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                else:
                    df = pd.read_excel(uploaded_file)
                
                # Store in session state
                st.session_state.uploaded_df = df
                
                # Check if duty data is present
                has_duty_data = any(col in df.columns for col in ['customs_value', 'unit_value', 'quantity'])
                
                # Validate
                is_valid, message = processor.validate_input_file(df, with_duties=has_duty_data)
                
                if not is_valid:
                    st.error(f"❌ {message}")
                    return
                
                st.success(f"✅ {message}")
                
                # Data preview
                st.subheader("📊 Data Preview")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Products", len(df))
                with col2:
                    if has_duty_data and 'customs_value' in df.columns:
                        total_value = df['customs_value'].sum() if 'customs_value' in df.columns else 0
                        st.metric("Total Customs Value", f"${total_value:,.2f}")
                    else:
                        st.metric("Duty Data", "Not Provided")
                with col3:
                    countries = df['origin'].nunique() if 'origin' in df.columns else 0
                    st.metric("Origin Countries", countries)
                
                # Show data preview with column selection
                preview_cols = st.multiselect(
                    "Select columns to preview",
                    options=df.columns.tolist(),
                    default=df.columns.tolist()[:8],
                    key="preview_cols"
                )
                
                if preview_cols:
                    st.dataframe(df[preview_cols].head(10), use_container_width=True, height=300)
                
                # Processing options
                st.subheader("⚙️ Processing Options")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Classification Settings**")
                    enable_fallback = st.checkbox(
                        "Enable AI Fallback",
                        value=True,
                        help="Use LLM when database confidence is low"
                    )
                    
                    search_depth = st.slider(
                        "Search Depth",
                        min_value=3,
                        max_value=10,
                        value=5,
                        help="Number of candidates to consider"
                    )
                
                with col2:
                    st.write("**Duty Calculation Settings**")
                    calculate_duties = st.checkbox(
                        "Calculate Import Duties",
                        value=has_duty_data,
                        help="Calculate duties if value data is available"
                    )
                    
                    if calculate_duties:
                        shipping_method = st.selectbox(
                            "Shipping Method",
                            ["sea", "air"],
                            help="Affects Harbor Maintenance Fee"
                        )
                        
                        col2a, col2b = st.columns(2)
                        with col2a:
                            include_mpf = st.checkbox("Include MPF", value=True)
                        with col2b:
                            include_hmf = st.checkbox("Include HMF", value=True)
                
                st.markdown("---")
                
                # Process button
                if st.button("🚀 Start Batch Processing", type="primary", use_container_width=True):
                    # Progress tracking
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    def update_progress(current, total, product_name):
                        progress = current / total
                        progress_bar.progress(progress)
                        status_text.text(f"Processing {current}/{total}: {product_name[:50]}...")
                    
                    # Process batch
                    with st.spinner("Processing batch..."):
                        start_time = time.time()
                        
                        # Configure processor
                        processor.fallback = st.session_state.fallback if enable_fallback else None
                        
                        # Process with or without duties
                        if calculate_duties:
                            results_df = processor.process_batch_with_duties(
                                df,
                                calculate_duties=True,
                                shipping_method=shipping_method,
                                include_mpf=include_mpf,
                                include_hmf=include_hmf,
                                progress_callback=update_progress
                            )
                        else:
                            results_df = processor.process_batch_with_duties(
                                df,
                                calculate_duties=False,
                                progress_callback=update_progress
                            )
                        
                        processing_time = time.time() - start_time
                    
                    # Clear progress
                    progress_bar.empty()
                    status_text.empty()
                    
                    # Store results
                    st.session_state.batch_results = results_df
                    st.session_state.batch_processing_time = processing_time
                    st.session_state.duty_calculation_enabled = calculate_duties
                    
                    if calculate_duties:
                        st.session_state.duty_summary = processor.generate_duty_summary(results_df)
                    
                    st.success(f"✅ Processing complete! {len(results_df)} products classified in {processing_time:.1f} seconds")
                    st.balloons()
                    
                    # Auto-switch to results tab
                    st.info("📊 Switch to the 'Results & Duties' tab to view your results")
                    
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
                with st.expander("Debug Information"):
                    st.code(str(e))
    
    with tab2:
        if 'batch_results' not in st.session_state:
            st.info("📤 Please upload and process a file first")
        else:
            st.subheader("📋 Classification & Duty Results")
            
            results_df = st.session_state.batch_results
            has_duties = st.session_state.get('duty_calculation_enabled', False)
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                success_count = len(results_df[results_df['classification_status'] == 'Success'])
                st.metric(
                    "Successful Classifications",
                    f"{success_count}/{len(results_df)}",
                    f"{(success_count/len(results_df)*100):.0f}%"
                )
            
            with col2:
                # Average confidence
                conf_values = []
                for conf in results_df['confidence']:
                    try:
                        val = float(str(conf).replace('%', ''))
                        if val > 0:
                            conf_values.append(val)
                    except:
                        pass
                avg_conf = sum(conf_values) / len(conf_values) if conf_values else 0
                st.metric("Avg Confidence", f"{avg_conf:.0f}%")
            
            with col3:
                if has_duties and 'total_duties' in results_df.columns:
                    total_duties = results_df['total_duties'].sum()
                    st.metric("Total Duties", f"${total_duties:,.2f}")
                else:
                    unique_codes = results_df['hs_code'].nunique()
                    st.metric("Unique HS Codes", unique_codes)
            
            with col4:
                if has_duties and 'total_landed_cost' in results_df.columns:
                    total_landed = results_df['total_landed_cost'].sum()
                    st.metric("Total Landed Cost", f"${total_landed:,.2f}")
                else:
                    processing_time = st.session_state.get('batch_processing_time', 0)
                    st.metric("Processing Time", f"{processing_time:.1f}s")
            
            # Display options
            st.subheader("📊 Results Table")
            
            # Column selection based on whether duties were calculated
            if has_duties:
                default_cols = ['product_name', 'hs_code', 'confidence', 'duty_rate', 
                               'customs_value', 'total_duties', 'total_landed_cost']
            else:
                default_cols = ['product_name', 'hs_code', 'confidence', 'duty_rate', 
                               'classification_status']
            
            # Filter out columns that don't exist
            default_cols = [col for col in default_cols if col in results_df.columns]
            
            display_cols = st.multiselect(
                "Select columns to display",
                options=results_df.columns.tolist(),
                default=default_cols,
                key="results_display_cols"
            )
            
            # Filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                status_filter = st.selectbox(
                    "Filter by Status",
                    ["All"] + results_df['classification_status'].unique().tolist(),
                    key="status_filter"
                )
            
            with col2:
                hs_filter = st.selectbox(
                    "Filter by HS Code",
                    ["All"] + sorted(results_df['hs_code'].unique().tolist()),
                    key="hs_filter"
                )
            
            with col3:
                if 'origin' in results_df.columns:
                    origin_filter = st.selectbox(
                        "Filter by Origin",
                        ["All"] + sorted(results_df['origin'].dropna().unique().tolist()),
                        key="origin_filter"
                    )
                else:
                    origin_filter = "All"
            
            # Apply filters
            filtered_df = results_df.copy()
            
            if status_filter != "All":
                filtered_df = filtered_df[filtered_df['classification_status'] == status_filter]
            if hs_filter != "All":
                filtered_df = filtered_df[filtered_df['hs_code'] == hs_filter]
            if origin_filter != "All" and 'origin' in filtered_df.columns:
                filtered_df = filtered_df[filtered_df['origin'] == origin_filter]
            
            # Display filtered results
            if len(filtered_df) < len(results_df):
                st.info(f"Showing {len(filtered_df)} of {len(results_df)} products")
            
            if display_cols:
                # Format currency columns for display
                display_df = filtered_df[display_cols].copy()
                
                # Format currency columns if they exist
                currency_cols = ['customs_value', 'base_duty', 'total_duties', 'total_landed_cost', 
                                'mpf', 'hmf', 'unit_value']
                for col in currency_cols:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) and x != 0 else "$0.00")
                
                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=400,
                    hide_index=True
                )
            
            # Export section
            st.subheader("📥 Export Options")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                # CSV export
                csv_data = filtered_df.to_csv(index=False)
                st.download_button(
                    label="📄 CSV Export",
                    data=csv_data,
                    file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                # Excel export with multiple sheets
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    # Main results
                    filtered_df.to_excel(writer, index=False, sheet_name='Results')
                    
                    # Summary sheet
                    if has_duties and 'duty_summary' in st.session_state:
                        summary = st.session_state.duty_summary
                        summary_data = {
                            'Metric': [
                                'Total Products',
                                'Successful Classifications',
                                'Total Customs Value',
                                'Total Import Duties',
                                'Total Landed Cost',
                                'Average Effective Duty Rate',
                                'Products with Duties',
                                'Duty-Free Products'
                            ],
                            'Value': [
                                len(filtered_df),
                                len(filtered_df[filtered_df['classification_status'] == 'Success']),
                                f"${summary.get('total_customs_value', 0):,.2f}",
                                f"${summary.get('total_duties', 0):,.2f}",
                                f"${summary.get('total_landed_cost', 0):,.2f}",
                                f"{summary.get('average_effective_rate', 0):.2f}%",
                                summary.get('products_with_duties', 0),
                                summary.get('products_duty_free', 0)
                            ]
                        }
                        pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name='Summary')
                    
                    # Format columns
                    for sheet in writer.sheets.values():
                        for column in sheet.columns:
                            max_length = 0
                            column_letter = column[0].column_letter
                            for cell in column:
                                try:
                                    if len(str(cell.value)) > max_length:
                                        max_length = len(str(cell.value))
                                except:
                                    pass
                            adjusted_width = min(max_length + 2, 50)
                            sheet.column_dimensions[column_letter].width = adjusted_width
                
                excel_data = excel_buffer.getvalue()
                st.download_button(
                    label="📊 Excel Export",
                    data=excel_data,
                    file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with col3:
                # JSON export
                json_data = filtered_df.to_json(orient='records', indent=2, date_format='iso')
                st.download_button(
                    label="📋 JSON Export",
                    data=json_data,
                    file_name=f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                    mime="application/json"
                )
            
            with col4:
                # Duty report (if applicable)
                if has_duties and 'duty_summary' in st.session_state:
                    duty_report = json.dumps(st.session_state.duty_summary, indent=2, default=str)
                    st.download_button(
                        label="💰 Duty Report",
                        data=duty_report,
                        file_name=f"duty_report_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                        mime="application/json"
                    )
    
    with tab3:
        if 'duty_summary' not in st.session_state:
            st.info("💰 Process a batch with duty calculation enabled to see analysis")
        else:
            st.subheader("📈 Duty Analysis Dashboard")
            
            summary = st.session_state.duty_summary
            results_df = st.session_state.batch_results
            
            # Overall duty metrics
            st.subheader("💵 Overall Duty Metrics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Customs Value",
                    f"${summary.get('total_customs_value', 0):,.2f}"
                )
            
            with col2:
                st.metric(
                    "Total Base Duties",
                    f"${summary.get('total_base_duty', 0):,.2f}",
                    f"{(summary.get('total_base_duty', 0)/summary.get('total_customs_value', 1)*100):.2f}%" if summary.get('total_customs_value', 0) > 0 else "0%"
                )
            
            with col3:
                st.metric(
                    "Total Fees (MPF+HMF)",
                    f"${(summary.get('total_mpf', 0) + summary.get('total_hmf', 0)):,.2f}"
                )
            
            with col4:
                st.metric(
                    "Total Landed Cost",
                    f"${summary.get('total_landed_cost', 0):,.2f}",
                    f"+{((summary.get('total_landed_cost', 0)-summary.get('total_customs_value', 0))/summary.get('total_customs_value', 1)*100):.1f}%" if summary.get('total_customs_value', 0) > 0 else "0%"
                )
            
            # Duty distribution charts
            st.subheader("📊 Duty Distribution")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart of duty components
                if summary.get('total_duties', 0) > 0:
                    fig_pie = go.Figure(data=[go.Pie(
                        labels=['Base Duty', 'MPF', 'HMF'],
                        values=[summary.get('total_base_duty', 0), summary.get('total_mpf', 0), summary.get('total_hmf', 0)],
                        hole=.3
                    )])
                    fig_pie.update_layout(
                        title="Duty Components Breakdown",
                        height=350
                    )
                    st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Bar chart of duties by country
                if summary.get('duty_by_country'):
                    countries = list(summary['duty_by_country'].get('total_duties', {}).keys())
                    duties = list(summary['duty_by_country'].get('total_duties', {}).values())
                    
                    if countries and duties:
                        fig_bar = go.Figure(data=[
                            go.Bar(x=countries, y=duties, marker_color='lightblue')
                        ])
                        fig_bar.update_layout(
                            title="Total Duties by Origin Country",
                            xaxis_title="Country",
                            yaxis_title="Total Duties ($)",
                            height=350
                        )
                        st.plotly_chart(fig_bar, use_container_width=True)
            
            # Top duty items
            if summary.get('highest_duty_items'):
                st.subheader("🔝 Highest Duty Items")
                highest_df = pd.DataFrame(summary['highest_duty_items'])
                
                # Format currency columns
                for col in ['customs_value', 'total_duties']:
                    if col in highest_df.columns:
                        highest_df[col] = highest_df[col].apply(lambda x: f"${x:,.2f}")
                
                st.table(highest_df)

def show_duty_calculator_page():
    st.markdown('<div class="main-header">💰 Duty & Fee Calculator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Calculate import duties and fees for your shipments</div>', unsafe_allow_html=True)

    calculator = st.session_state.calculator
    last_classification = st.session_state.classification_history[-1] if st.session_state.classification_history else None

    tab1, tab2, tab3 = st.tabs(["💵 Simple Calculator", "📄 Invoice-Based", "⚖️ Rate Comparison"])

    with tab1:
        st.subheader("Simple Duty Calculator")
        col1, col2 = st.columns(2)
        with col1:
            customs_value = st.number_input("Customs Value (USD)", min_value=0.0, value=10000.0, step=100.0,
                                            help="Total value of goods (CIF: Cost + Insurance + Freight)",
                                            key="simple_customs_value")
            default_rate = "0%"
            if last_classification and 'duty_rate' in last_classification:
                default_rate = last_classification['duty_rate']
            duty_rate = st.text_input("Duty Rate", value=default_rate,
                                      help="Enter rate from HTS (e.g., '5.5%' or 'Free')",
                                      key="simple_duty_rate")
        with col2:
            shipping_method = st.selectbox("Shipping Method", options=["sea", "air"],
                                           help="Affects Harbor Maintenance Fee calculation",
                                           key="simple_shipping")
            include_mpf = st.checkbox("Include MPF (Merchandise Processing Fee)", value=True, key="simple_mpf")
            include_hmf = st.checkbox("Include HMF (Harbor Maintenance Fee)", value=True, key="simple_hmf")

        if st.button("Calculate Duties", key="simple_calc", type="primary"):
            result = calculator.calculate_duties(
                customs_value=customs_value,
                duty_rate=duty_rate,
                shipping_method=shipping_method,
                include_mpf=include_mpf,
                include_hmf=include_hmf
            )
            display_duty_results(result, calculator)

    with tab2:
        st.subheader("Calculate from Invoice")
        st.write("Enter individual cost components to calculate CIF value automatically")

        col1, col2 = st.columns(2)
        with col1:
            fob_value = st.number_input("FOB Value (Product Cost)", min_value=0.0, value=8000.0, step=100.0,
                                        help="Free on Board - the cost of goods", key="invoice_fob")
            freight_cost = st.number_input("Freight Cost", min_value=0.0, value=1500.0, step=50.0,
                                           help="International shipping cost", key="invoice_freight")
            insurance_cost = st.number_input("Insurance Cost", min_value=0.0, value=500.0, step=50.0,
                                             help="Cargo insurance cost", key="invoice_insurance")
        with col2:
            duty_rate_invoice = st.text_input("Duty Rate", value="5.5%", key="duty_rate_invoice",
                                              help="Enter rate from HTS")
            shipping_method_invoice = st.selectbox("Shipping Method", options=["sea", "air"],
                                                   key="shipping_method_invoice")
            cif_preview = fob_value + freight_cost + insurance_cost
            st.metric("CIF Value (Calculated)", f"${cif_preview:,.2f}")

        if st.button("Calculate from Invoice", key="invoice_calc", type="primary"):
            result = calculator.calculate_from_invoice(
                fob_value=fob_value,
                freight_cost=freight_cost,
                insurance_cost=insurance_cost,
                duty_rate=duty_rate_invoice,
                shipping_method=shipping_method_invoice
            )
            st.subheader("Invoice Breakdown")
            inv_col1, inv_col2, inv_col3, inv_col4 = st.columns(4)
            inv = result['invoice_breakdown']
            inv_col1.metric("FOB Value", f"${inv['fob_value']:,.2f}")
            inv_col2.metric("Freight", f"${inv['freight_cost']:,.2f}")
            inv_col3.metric("Insurance", f"${inv['insurance_cost']:,.2f}")
            inv_col4.metric("CIF Value", f"${inv['cif_value']:,.2f}")
            display_duty_results(result, calculator)

    with tab3:
        st.subheader("Compare Standard vs Preferential Rates")
        st.write("Compare duties under normal rates vs Free Trade Agreements")
        col1, col2 = st.columns(2)
        with col1:
            comp_value = st.number_input("Customs Value (USD)", min_value=0.0, value=10000.0, step=100.0, key="comp_value")
            standard_rate = st.text_input("Standard Duty Rate", value="6.5%", help="Normal HTS rate", key="standard_rate")
        with col2:
            program = st.selectbox("Preferential Program",
                                   options=["USMCA (US-Mexico-Canada)", "GSP (Generalized System of Preferences)",
                                            "CAFTA-DR", "Other FTA"], key="program")
            preferential_rate = st.text_input("Preferential Rate", value="Free", help="Rate under the trade agreement",
                                              key="pref_rate")

        if st.button("Compare Rates", key="compare_calc", type="primary"):
            comparison = calculator.compare_rates(
                customs_value=comp_value,
                standard_rate=standard_rate,
                preferential_rate=preferential_rate,
                program_name=program
            )
            st.subheader("Comparison Results")
            comp_col1, comp_col2, comp_col3 = st.columns(3)
            with comp_col1:
                st.metric("Standard Duties", f"${comparison['standard']['total_duties_and_fees']:,.2f}")
            with col2:
                st.metric(f"{program} Duties", f"${comparison['preferential']['total_duties_and_fees']:,.2f}")
            with comp_col3:
                st.metric("Your Savings", f"${comparison['savings']:,.2f}", f"{comparison['savings_percent']:.1f}%")
            if comparison['savings'] > 0:
                st.success(f"💰 You save ${comparison['savings']:,.2f} by using {program}!")
            else:
                st.info("No savings with preferential rate")

    with st.expander("ℹ️ Understanding Import Duties & Fees"):
        st.markdown("""
        ### What's Included in Total Landed Cost?
        **1. Base Duty** – Tariff rate from the HTS  
        **2. MPF** – 0.3464% (min $27.75, max $538.40)  
        **3. HMF** – 0.125% (sea shipments only)
        """)

def display_duty_results(result, calculator):
    st.markdown("---")
    st.subheader("💵 Calculation Results")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Customs Value", calculator.format_currency(result['customs_value']))
    col2.metric("Total Duties & Fees", calculator.format_currency(result['total_duties_and_fees']))
    col3.metric("Total Landed Cost", calculator.format_currency(result['total_landed_cost']))
    col4.metric("Effective Rate", f"{result['effective_duty_rate']:.2f}%")

    st.subheader("Fee Breakdown")
    breakdown_df = {
        "Fee Type": ["Base Duty", "MPF", "HMF"],
        "Amount": [
            calculator.format_currency(result['base_duty']),
            calculator.format_currency(result['mpf']),
            calculator.format_currency(result['hmf'])
        ],
        "Rate": [
            result['duty_rate_applied'],
            f"{calculator.MPF_RATE*100:.4f}%",
            f"{calculator.HMF_RATE*100:.3f}%"
        ]
    }
    st.table(breakdown_df)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("📥 Download Calculation (JSON)", key="download_calc"):
            json_str = json.dumps(result, indent=2)
            st.download_button(
                label="Download",
                data=json_str,
                file_name=f"duty_calculation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                key="download_calc_btn"
            )

def show_analytics_page():
    st.markdown('<div class="main-header">📊 Classification Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Track performance and improve accuracy over time</div>', unsafe_allow_html=True)

    feedback_manager = st.session_state.feedback_manager
    analytics = AnalyticsEngine(feedback_manager)

    if feedback_manager.get_all_feedback().empty:
        st.info("📭 No feedback data yet. Start classifying products and collecting feedback to see analytics!")
        st.markdown("### Get Started\n1. Go to the Classifier page\n2. Classify some products\n3. Provide feedback on the results\n4. Return here to see insights!")
        return

    st.header("Overview")
    stats = analytics.get_overview_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("Total Classifications", f"{stats['total_classifications']:,}")
    with col2: st.metric("Accuracy Rate", f"{stats['accuracy_rate']:.1f}%")
    with col3: st.metric("Avg Confidence", f"{stats['avg_confidence']:.1f}%")
    with col4: st.metric("Feedback Received", f"{stats['total_feedback']:,}")

    st.markdown("---")
    st.header("Performance Analysis")
    col1, col2 = st.columns(2)
    with col1:
        conf_fig = analytics.get_confidence_distribution()
        if conf_fig: st.plotly_chart(conf_fig, use_container_width=True)
    with col2:
        acc_conf_fig = analytics.get_accuracy_by_confidence()
        if acc_conf_fig: st.plotly_chart(acc_conf_fig, use_container_width=True)
    rating_fig = analytics.get_rating_distribution()
    if rating_fig: st.plotly_chart(rating_fig, use_container_width=True)
    st.header("Usage Trends")
    trend_fig = analytics.get_classification_trends()
    if trend_fig: st.plotly_chart(trend_fig, use_container_width=True)
    st.header("Most Common Classifications")
    top_codes_fig = analytics.get_top_hs_codes(limit=15)
    if top_codes_fig: st.plotly_chart(top_codes_fig, use_container_width=True)
    st.header("⚠️ Misclassification Report")
    misclass_report = analytics.get_misclassification_report()
    if misclass_report is not None and not misclass_report.empty:
        st.write(f"Found {len(misclass_report)} misclassifications")
        st.dataframe(misclass_report, use_container_width=True, hide_index=True)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export Training Data", key="export_training"):
                output_file = feedback_manager.export_training_data()
                st.success(f"Training data exported to: {output_file}")
                st.info("Use this data to retrain or fine-tune your classification model")
    else:
        st.success("🎉 No misclassifications reported yet!")
    st.markdown("---")
    st.subheader("Export Data")
    col1, col2 = st.columns(2)
    df = feedback_manager.get_all_feedback()
    if not df.empty:
        with col1:
            st.download_button(
                label="📥 Download All Feedback (JSON)",
                data=df.to_json(orient='records', indent=2),
                file_name=f"feedback_data_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                key="download_json"
            )
        with col2:
            st.download_button(
                label="📥 Download All Feedback (CSV)",
                data=df.to_csv(index=False),
                file_name=f"feedback_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_csv"
            )

def show_about_page():
    st.markdown('<div class="main-header">📚 About HS Code Classifier</div>', unsafe_allow_html=True)
    if hasattr(st.session_state, 'enhancer'):
        model_name = getattr(st.session_state.enhancer, 'model_name', 'Unknown')
        st.info(f"🤖 Currently using AI Model: **{model_name}**")
    st.markdown("""
    ## AI-Powered Customs Classification System
    - **AI Classification** (Gemini) with automatic fallback
    - **Auto-Fill from Product Name** and **Image Auto-Fill**
    - **Vector Search** + **CROSS rulings**
    - **Confidence Scoring** + **Feedback loop**
    - **Duty Calculator** and **Analytics Dashboard**
    - **Batch Processing** with bulk duty calculation
    """)

if __name__ == "__main__":
    main()