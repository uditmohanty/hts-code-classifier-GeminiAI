import json
import pandas as pd
from datetime import datetime
from pathlib import Path

class FeedbackManager:
    def __init__(self, feedback_file='data/feedback/classifications_feedback.json'):
        self.feedback_file = Path(feedback_file)
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize file if it doesn't exist
        if not self.feedback_file.exists():
            self._save_feedback([])
    
    def _load_feedback(self):
        """Load all feedback records"""
        try:
            with open(self.feedback_file, 'r') as f:
                return json.load(f)
        except:
            return []
    
    def _save_feedback(self, feedback_list):
        """Save feedback records"""
        with open(self.feedback_file, 'w') as f:
            json.dump(feedback_list, f, indent=2)
    
    def add_feedback(self, classification_data, user_feedback):
        """
        Add new feedback entry
        
        Args:
            classification_data: dict with classification details
            user_feedback: dict with user's feedback
        """
        feedback_entry = {
            'timestamp': datetime.now().isoformat(),
            'classification_id': f"CLS-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'product_info': classification_data.get('product_info', {}),
            'predicted_code': classification_data.get('recommended_code'),
            'confidence': classification_data.get('confidence'),
            'user_rating': user_feedback.get('rating'),  # 1-5 stars or thumbs up/down
            'was_correct': user_feedback.get('was_correct'),  # True/False
            'actual_code': user_feedback.get('actual_code'),  # If user provides correct code
            'comments': user_feedback.get('comments', ''),
            'reasoning': classification_data.get('reasoning', '')
        }
        
        feedback_list = self._load_feedback()
        feedback_list.append(feedback_entry)
        self._save_feedback(feedback_list)
        
        return feedback_entry['classification_id']
    
    def get_all_feedback(self):
        """Get all feedback as DataFrame"""
        feedback_list = self._load_feedback()
        if not feedback_list:
            return pd.DataFrame()
        return pd.DataFrame(feedback_list)
    
    def get_accuracy_stats(self):
        """Calculate accuracy from feedback"""
        df = self.get_all_feedback()
        if df.empty:
            return None
        
        correct = df['was_correct'].sum()
        total = len(df)
        
        return {
            'total_classifications': total,
            'correct_classifications': correct,
            'accuracy': (correct / total * 100) if total > 0 else 0,
            'avg_confidence': df['confidence'].mean() if 'confidence' in df else 0
        }
    
    def get_misclassifications(self):
        """Get records where classification was wrong"""
        df = self.get_all_feedback()
        if df.empty:
            return pd.DataFrame()
        
        return df[df['was_correct'] == False]
    
    def export_training_data(self, output_file='data/feedback/training_data.json'):
        """Export feedback as training data for model improvement"""
        df = self.get_all_feedback()
        if df.empty:
            return None
        
        # Format for potential retraining
        training_data = []
        for _, row in df.iterrows():
            if row.get('actual_code'):  # Only include if user provided correct code
                training_data.append({
                    'input': {
                        'product_name': row['product_info'].get('product_name', ''),
                        'description': row['product_info'].get('description', ''),
                        'material': row['product_info'].get('material', ''),
                        'use': row['product_info'].get('use', '')
                    },
                    'correct_output': row['actual_code'],
                    'model_prediction': row['predicted_code'],
                    'was_correct': row['was_correct']
                })
        
        with open(output_file, 'w') as f:
            json.dump(training_data, f, indent=2)
        
        return output_file