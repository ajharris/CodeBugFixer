from dotenv import load_dotenv
import os

load_dotenv()

API_KEY = os.getenv('API_KEY')
STRIPE_TEST_KEY = os.getenv('STRIPE_TEST_KEY')
