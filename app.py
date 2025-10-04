import streamlit as st
import json
import os
import tempfile
from datetime import datetime
from src.agents.hs_code_agent import HSCodeAgent
from src.agents.fallback_analyzer import FallbackAnalyzer
from src.utils.report_generator import ReportGenerator
from src.utils.feedback_manager import FeedbackManager
from src.utils.analytics import AnalyticsEngine
from src.utils.duty_calculator import DutyCalculator
from src.utils.product_enhancer import ProductEnhancer
from src.utils.image_analyzer import ImageAnalyzer
import plotly.graph_objects as go
import plotly.express as px

# Page config
st.set_page_config(
    page_title="HS Code Classifier",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .confidence-high { color: #28a745; }
    .confidence-medium { color: #ffc107; }
    .confidence-low { color: #dc3545; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 1rem 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'classification_history' not in st.session_state:
    st.session_state.classification_history = []
if 'agent' not in st.session_state:
    with st.spinner("Initializing AI Agent..."):
        st.session_state.agent = HSCodeAgent()
        st.session_state.fallback = FallbackAnalyzer()
        st.session_state.feedback_manager = FeedbackManager()
        st.session_state.calculator = DutyCalculator()
        st.session_state.enhancer = ProductEnhancer()
        st.session_state.image_analyzer = ImageAnalyzer()

def main():
    """Main application entry point"""
    
    # Sidebar Navigation
    with st.sidebar:
        st.markdown("""
        <div style='text-align: center; padding: 1.5rem 0; background: linear-gradient(135deg, #1f77b4 0%, #2ca02c 100%); border-radius: 10px; margin-bottom: 1rem;'>
            <div style='font-size: 2.5rem; margin-bottom: 0.5rem;'>🌐</div>
            <div style='color: white; font-weight: bold; font-size: 1.2rem;'>HS CODE</div>
            <div style='color: #e0e0e0; font-size: 0.8rem;'>Classifier</div>
        </div>
        """, unsafe_allow_html=True)
        
        page = st.radio(
            "Navigation",
            ["🔍 Classifier", "💰 Duty Calculator", "📊 Analytics", "📚 About"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        
        # Quick stats
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
        
        st.markdown("---")
        st.caption("v1.0.0 | AI-Powered Classification")
    
    # Route to pages
    if page == "🔍 Classifier":
        show_classifier_page()
    elif page == "💰 Duty Calculator":
        show_duty_calculator_page()
    elif page == "📊 Analytics":
        show_analytics_page()
    elif page == "📚 About":
        show_about_page()

def show_classifier_page():
    """Product classification interface"""
    
    st.markdown('<div class="main-header">📦 HS Code Classification System</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">AI-powered customs classification for international trade</div>', unsafe_allow_html=True)
    
    # Input section
    st.subheader("Product Information")
    
    # Product name with auto-fill option
    col1, col2 = st.columns([3, 1])
    
    with col1:
        product_name = st.text_input(
            "Product Name *",
            placeholder="e.g., Men's Cotton T-Shirt",
            help="Enter the product name - AI can auto-fill the rest",
            key="product_name_input"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        auto_fill = st.button("🤖 Auto-Fill", type="secondary", use_container_width=True)
    
    # Initialize session state for auto-filled values
    if 'auto_filled_data' not in st.session_state:
        st.session_state.auto_filled_data = None
    if 'image_analysis' not in st.session_state:
        st.session_state.image_analysis = None
    
    # Handle auto-fill
    if auto_fill:
        if not product_name:
            st.warning("⚠️ Please enter a product name first")
        else:
            with st.spinner("🤖 AI is analyzing and generating detailed product information..."):
                enhanced_data = st.session_state.enhancer.enhance_product_info(product_name)
                
                if enhanced_data['success']:
                    st.session_state.auto_filled_data = enhanced_data
                    st.success("✨ Details auto-generated! Review and edit if needed.")
                else:
                    st.error(f"❌ Failed to auto-generate: {enhanced_data.get('error')}")
    
    # Get values (either auto-filled or empty)
    default_description = ""
    default_material = ""
    default_use = ""
    
    if st.session_state.auto_filled_data:
        default_description = st.session_state.auto_filled_data.get('description', '')
        default_material = st.session_state.auto_filled_data.get('material', '')
        default_use = st.session_state.auto_filled_data.get('intended_use', '')
    
    # Rest of the form
    col1, col2 = st.columns(2)
    
    with col1:
        material = st.text_input(
            "Material/Composition",
            value=default_material,
            placeholder="e.g., 100% Cotton",
            help="What is the product made of?",
            key="material_input"
        )
        
        origin = st.text_input(
            "Country of Origin",
            placeholder="e.g., Bangladesh",
            help="Where is the product manufactured?",
            key="origin_input"
        )
    
    with col2:
        description = st.text_area(
            "Detailed Description *",
            value=default_description,
            placeholder="Enter product features, size, style, function...",
            height=100,
            help="Provide as much detail as possible. Use Auto-Fill for AI assistance!",
            key="description_input"
        )
        
        use = st.text_input(
            "Intended Use",
            value=default_use,
            placeholder="e.g., Casual wear",
            help="What is this product used for?",
            key="use_input"
        )
    
    # Clear auto-fill button
    if st.session_state.auto_filled_data:
        if st.button("🔄 Clear Auto-Fill", key="clear_autofill"):
            st.session_state.auto_filled_data = None
            st.rerun()
    
    # Image upload with analysis
    st.markdown("---")
    st.subheader("🖼️ Product Image Analysis (Optional)")
    
    uploaded_file = st.file_uploader(
        "Upload Product Image",
        type=["jpg", "jpeg", "png"],
        help="Upload a product image for AI-powered analysis"
    )
    
    # Display and analyze image
    if uploaded_file is not None:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.image(uploaded_file, caption="Uploaded Product Image", use_column_width=True)
        
        with col2:
            st.write("")
            st.write("")
            analyze_image = st.button("🔍 Analyze Image", type="secondary", use_container_width=True)
        
        # Handle image analysis
        if analyze_image:
            with st.spinner("🖼️ AI is analyzing the product image..."):
                # Save uploaded file temporarily
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name
                
                # Analyze image
                image_result = st.session_state.image_analyzer.analyze_product_image(tmp_path)
                
                # Clean up temp file
                os.unlink(tmp_path)
                
                if image_result['success']:
                    st.success("✅ Image analyzed successfully!")
                    
                    # Store results
                    st.session_state.image_analysis = image_result
                    
                    # Display analysis
                    with st.expander("📋 Image Analysis Results", expanded=True):
                        st.write(f"**Product Identified:** {image_result['product_name']}")
                        st.write(f"**Material:** {image_result['material']}")
                        st.write(f"**Construction:** {image_result['construction']}")
                        st.write(f"**Description:** {image_result['description']}")
                        if image_result['features']:
                            st.write(f"**Features:** {', '.join(image_result['features'])}")
                        st.write(f"**Intended Use:** {image_result['intended_use']}")
                        if image_result['additional_notes']:
                            st.write(f"**Notes:** {image_result['additional_notes']}")
                else:
                    st.error(f"❌ Failed to analyze image: {image_result.get('error')}")
        
        # Button to use image analysis
        if st.session_state.image_analysis and st.session_state.image_analysis['success']:
            if st.button("📝 Use Image Data to Fill Form", type="primary", key="use_image_data"):
                st.session_state.auto_filled_data = {
                    'enhanced_name': st.session_state.image_analysis['product_name'],
                    'description': st.session_state.image_analysis['description'],
                    'material': st.session_state.image_analysis['material'],
                    'intended_use': st.session_state.image_analysis['intended_use'],
                    'success': True
                }
                st.success("✅ Form filled with image analysis data!")
                st.rerun()
    
    st.markdown("---")
    
    # Advanced options
    with st.expander("⚙️ Advanced Options"):
        col1, col2 = st.columns(2)
        with col1:
            search_depth = st.slider("Search Depth", 3, 10, 5)
        with col2:
            enable_fallback = st.checkbox("Enable Fallback Analysis", value=True)
    
    # Classification button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        classify_button = st.button("🔍 Classify Product", type="primary", use_container_width=True)
    
    if classify_button:
        if not product_name or not description:
            st.error("⚠️ Please enter at least Product Name and Description")
        else:
            with st.spinner("🤖 Analyzing product and applying GRI rules..."):
                # Prepare product info
                product_info = {
                    'product_name': product_name,
                    'description': description,
                    'material': material,
                    'use': use,
                    'origin': origin
                }
                
                # Classify
                result = st.session_state.agent.classify_product(product_info)
                
                # Check if fallback needed
                if enable_fallback and result.get('confidence', '0%') == '0%':
                    st.warning("Product not found in database. Using AI fallback analysis...")
                    result = st.session_state.fallback.analyze_unknown_product(product_info)
                
                # Add to history
                result['timestamp'] = datetime.now().isoformat()
                result['product_info'] = product_info
                st.session_state.classification_history.append(result)
                
                # Store for feedback
                st.session_state.current_result = result
                st.session_state.current_product_info = product_info
                
                # Display results
                display_results(result, product_info)

def display_results(result, product_info):
    """Display classification results"""
    
    st.success("✅ Classification Complete!")
    
    # Main result card
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
        confidence_val = float(confidence.replace('%', '')) if isinstance(confidence, str) else confidence
        
        if confidence_val >= 80:
            color_class = "confidence-high"
        elif confidence_val >= 60:
            color_class = "confidence-medium"
        else:
            color_class = "confidence-low"
        
        st.markdown(f'<h3 class="{color_class}">{confidence_val:.0f}%</h3>', unsafe_allow_html=True)
    
    # Confidence gauge
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=confidence_val,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Confidence Score"},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 60], 'color': "lightgray"},
                {'range': [60, 80], 'color': "gray"},
                {'range': [80, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))
    fig.update_layout(height=250)
    st.plotly_chart(fig, use_container_width=True)
    
    # Reasoning
    st.subheader("Classification Reasoning")
    st.write(result.get('reasoning', 'No reasoning provided'))
    
    # Alternative codes
    if result.get('alternatives'):
        st.subheader("Alternative HS Codes")
        for alt in result['alternatives']:
            st.write(f"- `{alt}`")
    
    # HTS Candidates
    if result.get('hts_candidates'):
        with st.expander("📊 HTS Database Matches"):
            for i, candidate in enumerate(result['hts_candidates'], 1):
                st.markdown(f"**{i}. {candidate['hs_code']}** (Relevance: {candidate['relevance_score']:.2f})")
                st.write(f"Description: {candidate['description']}")
                st.write(f"Duty Rate: {candidate['duty_rate']}")
                st.divider()
    
    # CROSS Rulings
    if result.get('cross_rulings'):
        with st.expander("📚 Relevant CROSS Rulings"):
            for ruling in result['cross_rulings']:
                st.markdown(f"**{ruling['ruling_number']}** - {ruling['date']}")
                st.write(f"HS Code: `{ruling['hs_code']}`")
                st.write(f"Summary: {ruling['description'][:200]}...")
                st.link_button("View Full Ruling", ruling['url'])
                st.divider()
    
    # Warning for low confidence
    if result.get('needs_review'):
        st.warning("⚠️ **Low Confidence Detection**: This classification should be reviewed by a customs broker.")
    
    # Export options
    st.subheader("Export Classification Report")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # JSON export
        report_generator = ReportGenerator()
        json_report = report_generator.generate_json_report(result, product_info)
        
        st.download_button(
            label="📥 Download JSON Report",
            data=json_report,
            file_name=f"hs_code_{product_info['product_name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            key="json_download"
        )
    
    with col2:
        # PDF export
        pdf_bytes = report_generator.generate_pdf_report(result, product_info)
        
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"hs_code_{product_info['product_name'].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            key="pdf_download"
        )
    
    # Feedback section
    st.markdown("---")
    display_feedback_section(result, product_info)

def display_feedback_section(result, product_info):
    """Display feedback collection interface"""
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
        rating = st.select_slider(
            "Rate this classification",
            options=[1, 2, 3, 4, 5],
            value=3,
            key="rating"
        )
        st.caption("⭐" * rating)
    
    actual_code = None
    if was_correct == False:
        actual_code = st.text_input(
            "What should the correct HS code be?",
            placeholder="e.g., 6203.42.40",
            help="If you know the correct code, please share it",
            key="actual_code"
        )
    
    comments = st.text_area(
        "Additional comments (optional)",
        placeholder="Any other feedback about this classification...",
        key="comments",
        height=100
    )
    
    if st.button("Submit Feedback", type="primary", key="submit_feedback"):
        if was_correct is None:
            st.warning("Please indicate if the classification was correct")
        else:
            # Save feedback
            user_feedback = {
                'rating': rating,
                'was_correct': was_correct,
                'actual_code': actual_code if actual_code else None,
                'comments': comments
            }
            
            classification_data = {
                'product_info': product_info,
                'recommended_code': result.get('recommended_code'),
                'confidence': result.get('confidence'),
                'reasoning': result.get('reasoning')
            }
            
            feedback_id = st.session_state.feedback_manager.add_feedback(classification_data, user_feedback)
            
            st.success(f"✅ Thank you for your feedback! (ID: {feedback_id})")

def show_duty_calculator_page():
    """Duty calculator interface"""
    st.markdown('<div class="main-header">💰 Duty & Fee Calculator</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Calculate import duties and fees for your shipments</div>', unsafe_allow_html=True)
    
    calculator = st.session_state.calculator
    
    # Get last classification if available
    last_classification = st.session_state.classification_history[-1] if st.session_state.classification_history else None
    
    # Tabs for different calculation methods
    tab1, tab2, tab3 = st.tabs(["💵 Simple Calculator", "📄 Invoice-Based", "⚖️ Rate Comparison"])
    
    with tab1:
        st.subheader("Simple Duty Calculator")
        
        col1, col2 = st.columns(2)
        
        with col1:
            customs_value = st.number_input(
                "Customs Value (USD)",
                min_value=0.0,
                value=10000.0,
                step=100.0,
                help="Total value of goods (CIF: Cost + Insurance + Freight)",
                key="simple_customs_value"
            )
            
            # Pre-fill duty rate if classification was done
            default_rate = "0%"
            if last_classification and 'duty_rate' in last_classification:
                default_rate = last_classification['duty_rate']
            
            duty_rate = st.text_input(
                "Duty Rate",
                value=default_rate,
                help="Enter rate from HTS (e.g., '5.5%' or 'Free')",
                key="simple_duty_rate"
            )
        
        with col2:
            shipping_method = st.selectbox(
                "Shipping Method",
                options=["sea", "air"],
                help="Affects Harbor Maintenance Fee calculation",
                key="simple_shipping"
            )
            
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
            fob_value = st.number_input(
                "FOB Value (Product Cost)",
                min_value=0.0,
                value=8000.0,
                step=100.0,
                help="Free on Board - the cost of goods",
                key="invoice_fob"
            )
            
            freight_cost = st.number_input(
                "Freight Cost",
                min_value=0.0,
                value=1500.0,
                step=50.0,
                help="International shipping cost",
                key="invoice_freight"
            )
            
            insurance_cost = st.number_input(
                "Insurance Cost",
                min_value=0.0,
                value=500.0,
                step=50.0,
                help="Cargo insurance cost",
                key="invoice_insurance"
            )
        
        with col2:
            duty_rate_invoice = st.text_input(
                "Duty Rate",
                value="5.5%",
                key="duty_rate_invoice",
                help="Enter rate from HTS"
            )
            
            shipping_method_invoice = st.selectbox(
                "Shipping Method",
                options=["sea", "air"],
                key="shipping_method_invoice"
            )
            
            # Show CIF calculation
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
            
            # Show invoice breakdown
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
            comp_value = st.number_input(
                "Customs Value (USD)",
                min_value=0.0,
                value=10000.0,
                step=100.0,
                key="comp_value"
            )
            
            standard_rate = st.text_input(
                "Standard Duty Rate",
                value="6.5%",
                help="Normal HTS rate",
                key="standard_rate"
            )
        
        with col2:
            program = st.selectbox(
                "Preferential Program",
                options=[
                    "USMCA (US-Mexico-Canada)",
                    "GSP (Generalized System of Preferences)",
                    "CAFTA-DR",
                    "Other FTA"
                ],
                key="program"
            )
            
            preferential_rate = st.text_input(
                "Preferential Rate",
                value="Free",
                help="Rate under the trade agreement",
                key="pref_rate"
            )
        
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
                st.metric(
                    "Standard Duties",
                    f"${comparison['standard']['total_duties_and_fees']:,.2f}"
                )
            
            with comp_col2:
                st.metric(
                    f"{program} Duties",
                    f"${comparison['preferential']['total_duties_and_fees']:,.2f}"
                )
            
            with comp_col3:
                st.metric(
                    "Your Savings",
                    f"${comparison['savings']:,.2f}",
                    f"{comparison['savings_percent']:.1f}%"
                )
            
            if comparison['savings'] > 0:
                st.success(f"💰 You save ${comparison['savings']:,.2f} by using {program}!")
            else:
                st.info("No savings with preferential rate")
    
    # Educational content
    with st.expander("ℹ️ Understanding Import Duties & Fees"):
        st.markdown("""
        ### What's Included in Total Landed Cost?
        
        **1. Base Duty**
        - Tariff rate from the HTS
        - Varies by product and country of origin
        - Can be reduced or eliminated with FTAs
        
        **2. MPF (Merchandise Processing Fee)**
        - 0.3464% of customs value
        - Minimum: $27.75
        - Maximum: $538.40
        - Applies to most imports
        
        **3. HMF (Harbor Maintenance Fee)**
        - 0.125% of customs value
        - Only for sea shipments
        - Not applicable to air cargo
        
        ### CIF Value
        Cost + Insurance + Freight = basis for duty calculation
        
        ### Preferential Programs
        - **USMCA**: US-Mexico-Canada Agreement
        - **GSP**: Developing countries preference
        - **FTAs**: Various free trade agreements
        
        Always verify current rates with CBP or a licensed broker.
        """)

def display_duty_results(result, calculator):
    """Display duty calculation results"""
    st.markdown("---")
    st.subheader("💵 Calculation Results")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric(
        "Customs Value",
        calculator.format_currency(result['customs_value'])
    )
    
    col2.metric(
        "Total Duties & Fees",
        calculator.format_currency(result['total_duties_and_fees'])
    )
    
    col3.metric(
        "Total Landed Cost",
        calculator.format_currency(result['total_landed_cost'])
    )
    
    col4.metric(
        "Effective Rate",
        f"{result['effective_duty_rate']:.2f}%"
    )
    
    # Detailed breakdown
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
    
    # Download option
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
    """Analytics dashboard"""
    st.markdown('<div class="main-header">📊 Classification Analytics Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Track performance and improve accuracy over time</div>', unsafe_allow_html=True)
    
    # Initialize analytics
    feedback_manager = st.session_state.feedback_manager
    analytics = AnalyticsEngine(feedback_manager)
    
    # Check if there's any data
    if feedback_manager.get_all_feedback().empty:
        st.info("📭 No feedback data yet. Start classifying products and collecting feedback to see analytics!")
        
        st.markdown("### Get Started")
        st.write("1. Go to the Classifier page")
        st.write("2. Classify some products")
        st.write("3. Provide feedback on the results")
        st.write("4. Return here to see insights!")
        return
    
    # Overview metrics
    st.header("Overview")
    stats = analytics.get_overview_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Classifications",
            f"{stats['total_classifications']:,}"
        )
    
    with col2:
        st.metric(
            "Accuracy Rate",
            f"{stats['accuracy_rate']:.1f}%"
        )
    
    with col3:
        st.metric(
            "Avg Confidence",
            f"{stats['avg_confidence']:.1f}%"
        )
    
    with col4:
        st.metric(
            "Feedback Received",
            f"{stats['total_feedback']:,}"
        )
    
    st.markdown("---")
    
    # Visualizations
    st.header("Performance Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        conf_fig = analytics.get_confidence_distribution()
        if conf_fig:
            st.plotly_chart(conf_fig, use_container_width=True)
    
    with col2:
        acc_conf_fig = analytics.get_accuracy_by_confidence()
        if acc_conf_fig:
            st.plotly_chart(acc_conf_fig, use_container_width=True)
    
    # Rating distribution
    rating_fig = analytics.get_rating_distribution()
    if rating_fig:
        st.plotly_chart(rating_fig, use_container_width=True)
    
    # Trends over time
    st.header("Usage Trends")
    trend_fig = analytics.get_classification_trends()
    if trend_fig:
        st.plotly_chart(trend_fig, use_container_width=True)
    
    # Top HS codes
    st.header("Most Common Classifications")
    top_codes_fig = analytics.get_top_hs_codes(limit=15)
    if top_codes_fig:
        st.plotly_chart(top_codes_fig, use_container_width=True)
    
    # Misclassification report
    st.header("⚠️ Misclassification Report")
    misclass_report = analytics.get_misclassification_report()
    
    if misclass_report is not None and not misclass_report.empty:
        st.write(f"Found {len(misclass_report)} misclassifications")
        
        st.dataframe(
            misclass_report,
            use_container_width=True,
            hide_index=True
        )
        
        # Export option
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Export Training Data", key="export_training"):
                output_file = feedback_manager.export_training_data()
                st.success(f"Training data exported to: {output_file}")
                st.info("Use this data to retrain or fine-tune your classification model")
    else:
        st.success("🎉 No misclassifications reported yet!")
    
    # Download feedback data
    st.markdown("---")
    st.subheader("Export Data")
    
    col1, col2 = st.columns(2)
    
    with col1:
        df = feedback_manager.get_all_feedback()
        if not df.empty:
            st.download_button(
                label="📥 Download All Feedback (JSON)",
                data=df.to_json(orient='records', indent=2),
                file_name=f"feedback_data_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                key="download_json"
            )
    
    with col2:
        if not df.empty:
            st.download_button(
                label="📥 Download All Feedback (CSV)",
                data=df.to_csv(index=False),
                file_name=f"feedback_data_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_csv"
            )

def show_about_page():
    """About page"""
    st.markdown('<div class="main-header">📚 About HS Code Classifier</div>', unsafe_allow_html=True)
    
    st.markdown("""
    ## AI-Powered Customs Classification System
    
    This advanced tool leverages artificial intelligence to classify products according to the 
    U.S. Harmonized Tariff Schedule (HTSUS), helping importers, exporters, and customs brokers 
    streamline the classification process.
    
    ### Core Features
    
    - **AI Classification**: Google Gemini-powered intelligent code assignment
    - **AI Auto-Fill**: Automatically generate detailed product descriptions
    - **Image Analysis**: Extract product details from photos using computer vision
    - **Vector Search**: Semantic search through complete HTSUS database (99 chapters)
    - **CROSS Integration**: References CBP ruling precedents
    - **GRI Application**: Applies General Rules of Interpretation
    - **Confidence Scoring**: Transparent confidence metrics
    - **Feedback Loop**: Continuous learning from user input
    - **Advanced Analytics**: Track performance over time
    - **Duty Calculator**: Estimate import costs and fees
    
    ### How It Works
    
    1. **Input**: Enter product name or upload image
    2. **Auto-Fill/Image Analysis**: AI generates detailed information
    3. **Vector Search**: Semantic matching with 768-dimensional embeddings
    4. **AI Analysis**: Gemini evaluates matches and applies GRI
    5. **Classification**: Receives HS code with reasoning
    6. **Feedback**: System learns from your corrections
    
    ### Technology Stack
    
    - **AI Model**: Google Gemini 2.5 Flash
    - **Embeddings**: all-mpnet-base-v2 (768 dimensions)
    - **Vector DB**: Pinecone
    - **Framework**: LangChain
    - **UI**: Streamlit
    
    ### Important Disclaimers
    
    ⚠️ **This tool is for informational purposes only**
    
    - Not a substitute for professional customs brokers
    - Final classification must be confirmed with U.S. Customs & Border Protection (CBP)
    - Duty rates are subject to change
    - Complex products may require manual review
    - Users remain responsible for accurate classification
    
    ### Accuracy & Limitations
    
    - **Estimated Accuracy**: 85-90% on standard products
    - **Best For**: Common consumer goods, textiles, electronics
    - **Limitations**: Complex machinery, chemicals, food products may need expert review
    
    ### Data Sources
    
    - HTSUS official database (all 99 chapters)
    - CBP CROSS ruling database
    - Updated: January 2025
    
    ### Support & Resources
    
    - **U.S. Customs**: https://www.cbp.gov
    - **Official HTSUS**: https://hts.usitc.gov
    - **CROSS Rulings**: https://rulings.cbp.gov
    
    ### Version Information
    
    - **Version**: 1.0.0
    - **Last Updated**: October 2025
    - **Model**: Gemini 2.5 Flash
    - **Embedding Model**: all-mpnet-base-v2
    
    ---
    
    **Questions or Issues?** Contact your development team or system administrator.
    """)
    
    # Usage statistics
    if st.session_state.classification_history:
        st.subheader("Your Usage Statistics")
        col1, col2, col3 = st.columns(3)
        
        col1.metric("Total Classifications", len(st.session_state.classification_history))
        
        feedback_df = st.session_state.feedback_manager.get_all_feedback()
        if not feedback_df.empty:
            col2.metric("Feedback Given", len(feedback_df))
            accuracy_stats = st.session_state.feedback_manager.get_accuracy_stats()
            if accuracy_stats:
                col3.metric("Your Accuracy", f"{accuracy_stats['accuracy']:.1f}%")

if __name__ == "__main__":
    main()