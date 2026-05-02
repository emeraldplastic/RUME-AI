"""Local entry point for RUME AI."""
from app.main import create_app

app = create_app()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  RUME AI - Secure Resume Screening")
    print("  Running at: http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(debug=True, host="127.0.0.1", port=5000)
