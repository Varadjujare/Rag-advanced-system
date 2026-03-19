"""Delete the old Endee index so it can be recreated with correct dimension."""
import os
from dotenv import load_dotenv
from endee import Endee

load_dotenv()

client = Endee(os.getenv("ENDEE_API_KEY"))
client.set_base_url(os.getenv("ENDEE_BASE_URL"))

COLLECTION = os.getenv("ENDEE_COLLECTION", "SmartDOC_PROD_Vault")

try:
    client.delete_index(name=COLLECTION)
    print(f"Deleted old index '{COLLECTION}' successfully.")
except Exception as e:
    print(f"Could not delete index (may not exist): {e}")

print("Done. The index will be auto-created on next PDF upload.")
