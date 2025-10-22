#!/usr/bin/env python3
"""
Create a sample receipt PDF for testing the receipt upload feature
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from datetime import datetime
import os

def create_test_receipt(filename='test_receipt.pdf'):
    """
    Create a simple test receipt PDF
    """
    # Create output directory if needed
    output_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'test_receipts')
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, filename)

    # Create PDF
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(2*inch, height - 1.5*inch, "PAYMENT RECEIPT")

    # Vendor info
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, height - 2.2*inch, "Amazon.com")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 2.5*inch, "410 Terry Ave North")
    c.drawString(1*inch, height - 2.7*inch, "Seattle, WA 98109")

    # Receipt details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 3.3*inch, "Receipt Details")

    c.setFont("Helvetica", 11)
    y_position = height - 3.7*inch

    # Date
    receipt_date = datetime.now().strftime('%Y-%m-%d')
    c.drawString(1.2*inch, y_position, f"Date:")
    c.drawString(3*inch, y_position, receipt_date)
    y_position -= 0.3*inch

    # Order number
    c.drawString(1.2*inch, y_position, f"Order #:")
    c.drawString(3*inch, y_position, "112-8234567-1234567")
    y_position -= 0.3*inch

    # Payment method
    c.drawString(1.2*inch, y_position, f"Payment Method:")
    c.drawString(3*inch, y_position, "Visa ending in 1234")
    y_position -= 0.5*inch

    # Items
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y_position, "Items Purchased")
    y_position -= 0.3*inch

    c.setFont("Helvetica", 10)
    c.drawString(1.2*inch, y_position, "1x USB-C Cable (6ft)")
    c.drawString(5.5*inch, y_position, "$12.99")
    y_position -= 0.25*inch

    c.drawString(1.2*inch, y_position, "1x Wireless Mouse")
    c.drawString(5.5*inch, y_position, "$24.99")
    y_position -= 0.25*inch

    c.drawString(1.2*inch, y_position, "2x AA Batteries (4-pack)")
    c.drawString(5.5*inch, y_position, "$15.98")
    y_position -= 0.25*inch

    # Subtotal
    c.line(1*inch, y_position - 0.1*inch, 6.5*inch, y_position - 0.1*inch)
    y_position -= 0.4*inch

    c.drawString(4.5*inch, y_position, "Subtotal:")
    c.drawString(5.5*inch, y_position, "$53.96")
    y_position -= 0.25*inch

    c.drawString(4.5*inch, y_position, "Tax (10%):")
    c.drawString(5.5*inch, y_position, "$5.40")
    y_position -= 0.25*inch

    c.drawString(4.5*inch, y_position, "Shipping:")
    c.drawString(5.5*inch, y_position, "$0.00")
    y_position -= 0.25*inch

    # Total
    c.line(4.5*inch, y_position - 0.1*inch, 6.5*inch, y_position - 0.1*inch)
    y_position -= 0.35*inch

    c.setFont("Helvetica-Bold", 12)
    c.drawString(4.5*inch, y_position, "TOTAL:")
    c.drawString(5.5*inch, y_position, "$59.36")

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(1*inch, 1*inch, "Thank you for your purchase!")
    c.drawString(1*inch, 0.8*inch, "Questions? Visit www.amazon.com/help")

    # Save PDF
    c.save()

    print(f"✅ Test receipt created: {filepath}")
    print(f"   File size: {os.path.getsize(filepath)} bytes")
    return filepath


def create_mining_payout_receipt(filename='test_mining_payout.pdf'):
    """
    Create a mining pool payout receipt for testing
    """
    # Create output directory if needed
    output_dir = os.path.join(os.path.dirname(__file__), 'uploads', 'test_receipts')
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, filename)

    # Create PDF
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1.5*inch, height - 1.5*inch, "MINING PAYOUT RECEIPT")

    # Pool info
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, height - 2.2*inch, "F2Pool")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 2.5*inch, "www.f2pool.com")

    # Payout details
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 3.1*inch, "Payout Details")

    c.setFont("Helvetica", 11)
    y_position = height - 3.5*inch

    # Date
    payout_date = datetime.now().strftime('%Y-%m-%d')
    c.drawString(1.2*inch, y_position, f"Payout Date:")
    c.drawString(3*inch, y_position, payout_date)
    y_position -= 0.3*inch

    # Coin
    c.drawString(1.2*inch, y_position, f"Cryptocurrency:")
    c.drawString(3*inch, y_position, "Bitcoin (BTC)")
    y_position -= 0.3*inch

    # Amount
    c.drawString(1.2*inch, y_position, f"Amount:")
    c.drawString(3*inch, y_position, "0.00125000 BTC")
    y_position -= 0.3*inch

    # USD value
    c.drawString(1.2*inch, y_position, f"USD Value:")
    c.drawString(3*inch, y_position, "$52.50 (@ $42,000/BTC)")
    y_position -= 0.3*inch

    # Wallet
    c.drawString(1.2*inch, y_position, f"Wallet Address:")
    c.setFont("Helvetica", 9)
    c.drawString(3*inch, y_position, "bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh")
    c.setFont("Helvetica", 11)
    y_position -= 0.3*inch

    # TX ID
    c.drawString(1.2*inch, y_position, f"Transaction ID:")
    c.setFont("Helvetica", 8)
    c.drawString(3*inch, y_position, "a1b2c3d4e5f6...")
    c.setFont("Helvetica", 11)
    y_position -= 0.5*inch

    # Mining stats
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, y_position, "Mining Statistics")
    y_position -= 0.3*inch

    c.setFont("Helvetica", 10)
    c.drawString(1.2*inch, y_position, "Period: Oct 15-21, 2025")
    y_position -= 0.25*inch

    c.drawString(1.2*inch, y_position, "Average Hashrate: 85.5 TH/s")
    y_position -= 0.25*inch

    c.drawString(1.2*inch, y_position, "Shares Accepted: 12,345")
    y_position -= 0.25*inch

    c.drawString(1.2*inch, y_position, "Pool Fee: 2.5%")
    y_position -= 0.25*inch

    # Footer
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(1*inch, 1*inch, "F2Pool - Leading Bitcoin Mining Pool")
    c.drawString(1*inch, 0.8*inch, "Support: support@f2pool.com")

    # Save PDF
    c.save()

    print(f"✅ Mining payout receipt created: {filepath}")
    print(f"   File size: {os.path.getsize(filepath)} bytes")
    return filepath


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Creating Test Receipts")
    print("="*60 + "\n")

    # Create both test receipts
    receipt1 = create_test_receipt()
    receipt2 = create_mining_payout_receipt()

    print("\n✅ All test receipts created successfully!")
    print("\nYou can now test the receipt upload feature with these files.")
