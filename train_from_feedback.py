from src.utils.feedback_manager import FeedbackManager

def analyze_feedback_for_training():
    """Analyze feedback to identify training opportunities"""
    fm = FeedbackManager()
    
    # Get misclassifications
    misclass = fm.get_misclassifications()
    
    if misclass.empty:
        print("No misclassifications to learn from yet")
        return
    
    print(f"Found {len(misclass)} misclassifications")
    print("\nCommon issues:")
    
    # Analyze patterns
    print(f"- Average confidence of wrong predictions: {misclass['confidence'].mean():.2%}")
    print(f"- Products needing review: {misclass['product_info'].apply(lambda x: x.get('product_name')).tolist()}")
    
    # Export for retraining
    training_file = fm.export_training_data()
    print(f"\nTraining data exported to: {training_file}")
    print("Next: Use this data to fine-tune your model or update embeddings")

if __name__ == "__main__":
    analyze_feedback_for_training()