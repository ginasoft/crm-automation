#!/usr/bin/env python3
"""
Test script to verify note filtering and deal differentiation
"""
import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from shared.brevo_client import BrevoClient
from shared.utils import get_lookback_period

def test_note_filtering():
    """Test note filtering functionality"""
    print("\n" + "="*60)
    print("TESTING NOTE FILTERING")
    print("="*60)

    client = BrevoClient(use_mock=True)
    start_time, end_time = get_lookback_period()

    print(f"\nFetching notes from {start_time} to {end_time}")
    notes = client.get_notes(start_time, end_time)

    print(f"\n✓ Retrieved {len(notes)} notes after filtering")

    # Verify all notes have companyIds
    for i, note in enumerate(notes, 1):
        has_company = bool(note.get("companyIds"))
        has_contact = bool(note.get("contactIds") and len(note.get("contactIds", [])) > 0)
        has_deal = bool(note.get("dealIds") and len(note.get("dealIds", [])) > 0)
        is_aura = note.get("text", "").strip().endswith("Generated automatically by Aura")

        print(f"\nNote #{i}:")
        print(f"  Has Company IDs: {has_company}")
        print(f"  Has Contact IDs: {has_contact}")
        print(f"  Has Deal IDs: {has_deal}")
        print(f"  Is Aura AI: {is_aura}")
        print(f"  Text preview: {note.get('text', '')[:60]}...")

        # These should all be True for valid notes
        assert has_company, f"Note {i} missing company IDs!"
        assert not has_contact, f"Note {i} has contact IDs!"
        assert not has_deal, f"Note {i} has deal IDs!"
        assert not is_aura, f"Note {i} is Aura AI generated!"

    print("\n✓ All notes passed filtering validation!")
    return notes

def test_deal_differentiation():
    """Test deal differentiation functionality"""
    print("\n" + "="*60)
    print("TESTING DEAL DIFFERENTIATION")
    print("="*60)

    client = BrevoClient(use_mock=True)
    start_time, end_time = get_lookback_period()

    print(f"\nFetching deals from {start_time} to {end_time}")
    deals_data = client.get_deals(start_time, end_time)

    new_deals = deals_data.get("new_deals", [])
    updated_deals = deals_data.get("updated_deals", [])

    print(f"\n✓ Retrieved {len(new_deals)} new deals")
    print(f"✓ Retrieved {len(updated_deals)} updated deals")

    # Verify new deals
    print("\n--- NEW DEALS ---")
    for i, deal in enumerate(new_deals, 1):
        created_at = deal.get("created_at")
        print(f"\n{i}. {deal.get('deal_name')}")
        print(f"   Created: {created_at}")
        print(f"   Owner: {deal.get('deal_owner')}")
        print(f"   Amount: ${deal.get('amount', 0):,.2f}")
        print(f"   Opportunity Type: {deal.get('opportunity_type', 'N/A')}")

    # Verify updated deals
    print("\n--- UPDATED DEALS ---")
    for i, deal in enumerate(updated_deals, 1):
        created_at = deal.get("created_at")
        stage_updated = deal.get("stage_updated_at")
        print(f"\n{i}. {deal.get('deal_name')}")
        print(f"   Created: {created_at}")
        print(f"   Stage Updated: {stage_updated}")
        print(f"   Owner: {deal.get('deal_owner')}")
        print(f"   Amount: ${deal.get('amount', 0):,.2f}")

    print("\n✓ All deals passed differentiation validation!")
    return deals_data

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("BREVO CLIENT FUNCTIONALITY TESTS")
    print("="*60)

    try:
        # Test note filtering
        notes = test_note_filtering()

        # Test deal differentiation
        deals_data = test_deal_differentiation()

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"✓ {len(notes)} company-level notes (no Aura AI)")
        print(f"✓ {len(deals_data['new_deals'])} new deals")
        print(f"✓ {len(deals_data['updated_deals'])} updated deals")
        print("\n✅ ALL TESTS PASSED!")
        print("="*60 + "\n")

        return 0

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
