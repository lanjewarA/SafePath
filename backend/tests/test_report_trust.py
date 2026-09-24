import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.llm.report_trust import evaluate_report_credibility

client = TestClient(app)

# Planted Benchmark Dataset: 5 Genuine Safety Hazards vs 5 Fake/Spam Submissions
PLANTED_BENCHMARK_REPORTS = [
    # Genuine Safety Reports (Expected: is_trustworthy == True)
    {"location": "Dadar West Flyover, Mumbai", "type": "poor_lighting", "text": "Streetlight on the west exit of the flyover has been out for 3 days, making the stairs extremely dark after 8 PM.", "expected_trustworthy": True},
    {"location": "Lower Parel Station Exit", "type": "isolated_area", "text": "Pedestrian underpass has no functional CCTV and no crowd activity late at night.", "expected_trustworthy": True},
    {"location": "Senapati Bapat Marg", "type": "harassment_risk", "text": "Isolated alleyway near construction site with broken streetlights and poor visibility.", "expected_trustworthy": True},
    {"location": "Mahim Junction Footbridge", "type": "cctv_broken", "text": "Surveillance camera dome is shattered and dark walkway is unmonitored.", "expected_trustworthy": True},
    {"location": "Prabhadevi Chowk", "type": "poor_lighting", "text": "Dark alleyway behind bus stop has zero working lights and high shadows.", "expected_trustworthy": True},

    # Planted Fake / Spam Reports (Expected: is_trustworthy == False)
    {"location": "Random Place", "type": "spam", "text": "asdfqwerty 12345", "expected_trustworthy": False},
    {"location": "Unknown", "type": "spam", "text": "Buy free crypto tokens and casino discounts today!", "expected_trustworthy": False},
    {"location": "Test Loc", "type": "test", "text": "hi", "expected_trustworthy": False},
    {"location": "Everywhere", "type": "spam", "text": "test test test 123 123 123", "expected_trustworthy": False},
    {"location": "Flyover", "type": "spam", "text": "Great discount offer on online shopping click here!", "expected_trustworthy": False},
]

def test_gemini_report_trust_precision_and_recall():
    tp = 0  # True Positives: Genuine correctly approved
    fp = 0  # False Positives: Fake incorrectly approved
    tn = 0  # True Negatives: Fake correctly rejected
    fn = 0  # False Negatives: Genuine incorrectly rejected

    for item in PLANTED_BENCHMARK_REPORTS:
        res = evaluate_report_credibility(
            location=item["location"],
            report_type=item["type"],
            description=item["text"]
        )
        is_trust = res.get("is_trustworthy", False)
        expected = item["expected_trustworthy"]

        if expected and is_trust:
            tp += 1
        elif not expected and is_trust:
            fp += 1
        elif not expected and not is_trust:
            tn += 1
        elif expected and not is_trust:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    f1_score = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    print(f"\n[Planted Benchmark Evaluation] TP: {tp}, FP: {fp}, TN: {tn}, FN: {fn}")
    print(f"[Planted Benchmark Evaluation] Filter Precision: {precision:.4f}, Recall: {recall:.4f}, F1 Score: {f1_score:.4f}")

    # Enforce minimum precision and recall benchmarks >= 0.80
    assert precision >= 0.80, f"Precision {precision} below 0.80 threshold!"
    assert recall >= 0.80, f"Recall {recall} below 0.80 threshold!"

def test_submit_report_api_endpoint():
    # Submit genuine report
    genuine_payload = {
        "user_id": "usr_test_001",
        "segment_id": "seg-mh-1001",
        "location_landmark": "Dadar West Station Exit",
        "report_type": "poor_lighting",
        "description": "Streetlight out near station exit stairs, area is dark and unmonitored."
    }
    resp = client.post("/api/reports/submit", json=genuine_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["is_trustworthy"] is True

    # Submit spam report
    spam_payload = {
        "user_id": "usr_spammer_99",
        "segment_id": "seg-mh-1002",
        "location_landmark": "Anywhere",
        "report_type": "spam",
        "description": "asdfqwerty test 123"
    }
    resp_spam = client.post("/api/reports/submit", json=spam_payload)
    assert resp_spam.status_code == 200
    data_spam = resp_spam.json()
    assert data_spam["status"] == "rejected"
    assert data_spam["is_trustworthy"] is False
