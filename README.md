# DELTA CFO AGENT - AI-POWERED FINANCIAL PLATFORM

AI-powered financial transaction processing and management system for Delta businesses with SQLite backend and Claude API integration.

## 🚀 PROCESSING OPTIONS

### Database-First Approach (Recommended)
```bash
python3 main_db.py your_file.csv               # Process and store in SQLite
python3 ai_identifier_service.py --process-all # Generate AI identifiers
cd web_ui && python3 app.py                    # Launch web dashboard
```

### Legacy CSV Processing
```bash
python3 main.py your_file.csv --enhance --merge  # Process and merge to master CSV
```

### What Enhanced Processing Does
1. 🔍 **Classifies transactions** using business rules and AI
2. 📍 **Adds Origin/Destination** tracking for all transactions
3. 🆔 **Extracts meaningful identifiers** (TxID, counterparty names, reference numbers)
4. 💰 **Converts crypto amounts to USD** (BTC, TAO, ETH, USDC, etc.)
5. 🏦 **Identifies specific accounts** (Coinbase, Checking ...3911, etc.)
6. 🔀 **Safely consolidates** to MASTER_TRANSACTIONS.csv with duplicate detection

## 🖥️ WEB DASHBOARD

```bash
cd web_ui && python3 app.py
# Open http://localhost:5000
```

**Features:**
- 📊 Transaction table with inline keyword filtering
- 💰 Currency badges (BTC/TAO/USD)
- 🔍 Click any keyword to filter similar transactions
- 📈 Real-time totals and entity summaries

## 🏢 BUSINESS ENTITIES

| Entity | Purpose | Account Types |
|--------|---------|---------------|
| **Delta LLC** | US Holding Company | Chase ...3687, Business accounts |
| **Delta Prop Shop LLC** | Trading Operations | Coinbase, MEXC, TAO trading |
| **Infinity Validator** | Bitcoin Mining | BTC mining rewards, Subnet 89 |
| **Delta Mining Paraguay S.A.** | Paraguay Operations | Wire transfers, ANDE payments |
| **Delta Brazil** | Brazil Operations | Employee payments, Porto Seguro |
| **Personal** | Owner Personal | Personal cards, individual expenses |

## 🚀 NEXT ENHANCEMENTS

1. **Automated invoice parsing** from email attachments
2. **Multi-entity consolidation** reports
3. **SAFE note investor tracking**
4. **Series A preparation** tools