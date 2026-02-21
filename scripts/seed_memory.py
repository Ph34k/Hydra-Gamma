import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.memory.semantic import SemanticMemory

def seed():
    print("Seeding memory...")
    memory = SemanticMemory()

    articles = [
        {
            "title": "Reset Password",
            "content": "To reset your password, go to Settings > Account > Security and click 'Reset Password'. You will receive an email with a link.",
            "metadata": {"category": "account", "id": "KB001"}
        },
        {
            "title": "API Rate Limits",
            "content": "The API rate limit is 100 requests per minute for free tier and 1000 for pro tier. Exceeding this will result in a 429 error.",
            "metadata": {"category": "api", "id": "KB002"}
        },
        {
            "title": "Billing Issues",
            "content": "If you are charged incorrectly, please contact support@example.com with your invoice number. Refunds are processed within 5-7 business days.",
            "metadata": {"category": "billing", "id": "KB003"}
        },
         {
            "title": "Python SDK Installation",
            "content": "To install the Python SDK, run `pip install myapp-sdk`. Requires Python 3.8 or higher.",
            "metadata": {"category": "dev", "id": "KB004"}
        }
    ]

    for article in articles:
        print(f"Indexing: {article['title']}")
        memory.index_document(
            text=f"Title: {article['title']}\nContent: {article['content']}",
            metadata=article['metadata'],
            source="knowledge_base"
        )

    print("Memory seeding complete.")

if __name__ == "__main__":
    seed()
