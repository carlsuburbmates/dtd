import os
import sys
import time
import requests
from pymongo import MongoClient

BACKEND_URL = "http://localhost:8000"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "dtd")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "change-me")

def main():
    print("=== Starting Actual-Domain Activation Slice Verification ===")
    
    # 1. Ensure backend is up
    try:
        requests.get(f"{BACKEND_URL}/health", timeout=2.0)
    except Exception:
        print(f"Error: Backend is not reachable at {BACKEND_URL}.")
        sys.exit(1)

    print("\n1. Submitting a controlled trainer record through the statutory and quality gates...")
    test_email = "carl.g+stripe-resend-test@dogtrainersdirectory.com.au"
    submit_payload = {
        "name": "Activation Test Trainer",
        "suburb": "Melbourne",
        "region": "Greater Melbourne",
        "email": test_email,
        "website": "https://www.activationtest.com.au",
        "phone": "0400000000",
        "services": ["Puppy Training", "Obedience"],
        "bio": "This is a comprehensive bio to ensure a good score. We are testing the integration. We are professional trainers based in Melbourne.",
        "consent_public_listing": True,
        "consent_information_accuracy": True,
        "consent_intro_billing_terms": True
    }
    
    resp = requests.post(f"{BACKEND_URL}/api/submissions", json=submit_payload)
    if resp.status_code != 200:
        print(f"Submission failed! {resp.status_code} - {resp.text}")
        sys.exit(1)
        
    data = resp.json()
    print(f"Submission Response: {data}")
    trainer_id = data.get("trainer_id")
    if not trainer_id:
        print("Error: No trainer_id returned. The submission may have been held by the evidence gate.")
        sys.exit(1)
        
    print(f"-> Submission accepted with trainer_id: {trainer_id}, status: {data.get('status')}, confidence: {data.get('confidence_score')}")
    
    # Wait briefly for any async billing setup in the background (though provision_trainer_billing_profile is awaited)
    time.sleep(2)
    
    print("\n2. Simulating a user intro request to trigger Stripe billing & Resend notification...")
    intro_payload = {
        "trainer_id": trainer_id,
        "name": "Test Owner",
        "email": "owner.test@example.com",
        "phone": "0412345678",
        "dog_name": "Buddy",
        "dog_breed": "Labrador",
        "description": "Need help with pulling on leash.",
        "consent_contact_release": True,
        "consent_outcome_tracking": True
    }
    
    resp = requests.post(f"{BACKEND_URL}/api/intros", json=intro_payload)
    if resp.status_code != 200:
        print(f"Intro creation failed! {resp.status_code} - {resp.text}")
        sys.exit(1)
        
    intro_data = resp.json()
    intro_id = intro_data.get("id")
    print(f"-> Success! Intro created with id: {intro_id}")
    
    print("\n3. Validating Database State...")
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Check Trainer Billing State
    trainer = db.trainers.find_one({"id": trainer_id})
    stripe_customer_id = trainer.get("stripe_customer_id")
    print(f"Trainer stripe_customer_id: {stripe_customer_id}")
    if not stripe_customer_id:
        print("Error: Stripe Customer ID was not attached to the trainer.")
    else:
        print("-> Stripe Customer successfully provisioned.")
        
    # Check Intro Billing State
    intro = db.intros.find_one({"id": intro_id})
    stripe_invoice_id = intro.get("stripe_invoice_id")
    print(f"Intro stripe_invoice_id: {stripe_invoice_id}")
    print(f"Intro billing_status: {intro.get('billing_status')}")
    if stripe_invoice_id:
        print("-> Stripe Invoice successfully generated for the intro.")
    else:
        print("Error or Note: No Stripe Invoice generated. (Check if intro billing is disabled or if trainer is on a free trial)")
        
    # Check Notification State
    notif = db.notification_events.find_one({"kind": "trainer_intro_notification", "target_id": intro_id})
    if notif:
        print(f"-> Resend Notification dispatched successfully! Event ID: {notif.get('id')}, Provider ID: {notif.get('provider_id')}")
    else:
        print("Error: No notification event found for this intro.")
        
    print("\n=== Activation Slice Test Completed ===")
    
if __name__ == "__main__":
    main()
