from app.main import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Ensure data and upload directories exist
    os.makedirs('data', exist_ok=True)
    os.makedirs('uploads', exist_ok=True)
    
    print("\n" + "="*60)
    print("  RUME AI \u2014 AI-Powered Resume Screening Platform")
    print("  Running at: http://127.0.0.1:5000")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000)
