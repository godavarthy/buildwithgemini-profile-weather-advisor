#!/usr/bin/env python3
"""
Seed script to populate 'my_details' in Firestore database 'my-db' with the 3 sample rows.
Project ID: qwiklabs-gcp-04-d5a16181d919 (hardcoded string)
"""

from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-d5a16181d919"
DATABASE_NAME = "my-db"
COLLECTION_NAME = "my_details"


def seed():
    db = firestore.Client(project=PROJECT_ID, database=DATABASE_NAME)
    sample_records = [
        {
            "id": "kids",
            "name": "kids",
            "govt_id": "123",
            "age": 10,
            "allow_social_media": False,
            "photo": "https://storage.googleapis.com/bwg3-qwiklabs-gcp-04-d5a16181d919/profile_photos/kids.png",
            "suggestion": "no social media for you kiddo",
            "bg_color": "baby pink",
        },
        {
            "id": "parents",
            "name": "parents",
            "govt_id": "345",
            "age": 30,
            "allow_social_media": True,
            "photo": "https://storage.googleapis.com/bwg3-qwiklabs-gcp-04-d5a16181d919/profile_photos/parents.png",
            "suggestion": "pls focus on building agents and stop wasting time on social media",
            "bg_color": "light yellow",
        },
        {
            "id": "grand_parents",
            "name": "grand parents",
            "govt_id": "897",
            "age": 60,
            "allow_social_media": True,
            "photo": "https://storage.googleapis.com/bwg3-qwiklabs-gcp-04-d5a16181d919/profile_photos/grand_parents.png",
            "suggestion": "for your better health, pls use for around 1 hour maximum per day",
            "bg_color": "light blue",
        },
    ]

    for record in sample_records:
        doc_id = record["id"].replace(" ", "_")
        data = {k: v for k, v in record.items() if k != "id"}
        db.collection(COLLECTION_NAME).document(doc_id).set(data)
        print(f"Seeded document: {doc_id} -> {data}")

    print("Successfully seeded all 3 sample rows into Firestore!")


if __name__ == "__main__":
    seed()
