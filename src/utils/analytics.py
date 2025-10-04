import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import Counter

class AnalyticsEngine:
    def __init__(self, feedback_manager):
        self.feedback_manager = feedback_manager
        self.df = feedback_manager.get_all_feedback()
    
    def get_overview_stats(self):
        """Get high-level statistics"""
        if self.df.empty:
            return {
                'total_classifications': 0,
                'accuracy_rate': 0,
                'avg_confidence': 0,
                'total_feedback': 0
            }
        
        return {
            'total_classifications': len(self.df),
            'accuracy_rate': (self.df['was_correct'].sum() / len(self.df) * 100) if len(self.df) > 0 else 0,
            'avg_confidence': self.df['confidence'].mean() * 100 if 'confidence' in self.df.columns else 0,
            'total_feedback': len(self.df)
        }
    
    def get_confidence_distribution(self):
        """Plot confidence score distribution"""
        if self.df.empty or 'confidence' not in self.df.columns:
            return None
        
        fig = px.histogram(
            self.df,
            x='confidence',
            nbins=20,
            title='Confidence Score Distribution',
            labels={'confidence': 'Confidence Score', 'count': 'Number of Classifications'},
            color_discrete_sequence=['#1f77b4']
        )
        
        fig.update_layout(
            xaxis_title="Confidence Score",
            yaxis_title="Count",
            showlegend=False
        )
        
        return fig
    
    def get_accuracy_by_confidence(self):
        """Show accuracy vs confidence correlation"""
        if self.df.empty:
            return None
        
        # Bin confidence scores
        self.df['confidence_bin'] = pd.cut(self.df['confidence'], bins=[0, 0.5, 0.7, 0.85, 1.0], 
                                           labels=['Low (<50%)', 'Medium (50-70%)', 'High (70-85%)', 'Very High (>85%)'])
        
        accuracy_by_conf = self.df.groupby('confidence_bin')['was_correct'].mean() * 100
        
        fig = go.Figure(data=[
            go.Bar(
                x=accuracy_by_conf.index.astype(str),
                y=accuracy_by_conf.values,
                marker_color=['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4']
            )
        ])
        
        fig.update_layout(
            title='Accuracy by Confidence Level',
            xaxis_title='Confidence Range',
            yaxis_title='Accuracy (%)',
            yaxis_range=[0, 100]
        )
        
        return fig
    
    def get_top_hs_codes(self, limit=10):
        """Most frequently classified HS codes"""
        if self.df.empty:
            return None
        
        code_counts = self.df['predicted_code'].value_counts().head(limit)
        
        fig = px.bar(
            x=code_counts.values,
            y=code_counts.index,
            orientation='h',
            title=f'Top {limit} Most Classified HS Codes',
            labels={'x': 'Count', 'y': 'HS Code'},
            color_discrete_sequence=['#2ca02c']
        )
        
        fig.update_layout(yaxis={'categoryorder': 'total ascending'})
        
        return fig
    
    def get_classification_trends(self):
        """Classifications over time"""
        if self.df.empty:
            return None
        
        self.df['date'] = pd.to_datetime(self.df['timestamp']).dt.date
        daily_counts = self.df.groupby('date').size().reset_index(name='count')
        
        fig = px.line(
            daily_counts,
            x='date',
            y='count',
            title='Classifications Over Time',
            labels={'date': 'Date', 'count': 'Number of Classifications'},
            markers=True
        )
        
        return fig
    
    def get_rating_distribution(self):
        """User rating distribution"""
        if self.df.empty or 'user_rating' not in self.df.columns:
            return None
        
        rating_counts = self.df['user_rating'].value_counts().sort_index()
        
        fig = go.Figure(data=[
            go.Bar(
                x=['⭐' * i for i in rating_counts.index],
                y=rating_counts.values,
                marker_color='gold'
            )
        ])
        
        fig.update_layout(
            title='User Satisfaction Ratings',
            xaxis_title='Rating',
            yaxis_title='Count'
        )
        
        return fig
    
    def get_misclassification_report(self):
        """Detailed report of misclassifications"""
        if self.df.empty:
            return None
        
        misclassified = self.df[self.df['was_correct'] == False].copy()
        
        if misclassified.empty:
            return None
        
        # Add product names for context
        misclassified['product_name'] = misclassified['product_info'].apply(
            lambda x: x.get('product_name', 'N/A') if isinstance(x, dict) else 'N/A'
        )
        
        report = misclassified[[
            'timestamp', 'product_name', 'predicted_code', 
            'actual_code', 'confidence', 'comments'
        ]].sort_values('timestamp', ascending=False)
        
        return report