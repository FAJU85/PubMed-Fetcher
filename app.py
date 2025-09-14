import os
import time
import threading
from flask import Flask, jsonify
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# ===== CONFIGURE THESE =====
API_KEY = "8fdc69a521cc163da6e892d0d3e214880608"
EMAIL = "assim.alfadda@ksu.edu.sa"  # ← YOUR REAL EMAIL
SHEET_ID = "1rizbL69aBz1gC746U2iJy5k3lIYlk9vRRZCogk174sg"  # ← YOUR SHEET ID
AUTHOR_NAME = "Alfadda AA"

# Google Sheets credentials
GOOGLE_CREDS_FILE = "service-account.json"

# Journal metadata
JOURNAL_METADATA = {
    'Nature': {'impactFactor': 64.8, 'quartile': 'Q1'},
    'Science': {'impactFactor': 56.9, 'quartile': 'Q1'},
    'Cell': {'impactFactor': 66.85, 'quartile': 'Q1'},
    'Nature Medicine': {'impactFactor': 87.24, 'quartile': 'Q1'},
    'Nature Genetics': {'impactFactor': 41.307, 'quartile': 'Q1'},
    'Nature Reviews Endocrinology': {'impactFactor': 31.062, 'quartile': 'Q1'},
    'Diabetes': {'impactFactor': 9.127, 'quartile': 'Q1'},
    'Diabetologia': {'impactFactor': 10.460, 'quartile': 'Q1'},
    'Journal of Clinical Investigation': {'impactFactor': 19.456, 'quartile': 'Q1'},
    'American Journal of Clinical Nutrition': {'impactFactor': 8.472, 'quartile': 'Q1'},
    'New England Journal of Medicine': {'impactFactor': 176.079, 'quartile': 'Q1'},
    'The Lancet': {'impactFactor': 202.731, 'quartile': 'Q1'},
    'JAMA': {'impactFactor': 120.7, 'quartile': 'Q1'},
    'BMC Medicine': {'impactFactor': 9.3, 'quartile': 'Q1'},
    'Circulation': {'impactFactor': 29.69, 'quartile': 'Q1'},
    'Diabetes Care': {'impactFactor': 19.112, 'quartile': 'Q1'},
    'Obesity': {'impactFactor': 5.002, 'quartile': 'Q2'},
    'International Journal of Obesity': {'impactFactor': 4.419, 'quartile': 'Q2'},
    'Metabolism': {'impactFactor': 5.229, 'quartile': 'Q2'},
    'Nutrients': {'impactFactor': 5.717, 'quartile': 'Q2'},
    'Scientific Reports': {'impactFactor': 4.996, 'quartile': 'Q2'},
    'Journal of Nutritional Biochemistry': {'impactFactor': 5.44, 'quartile': 'Q2'},
    'Clinical Nutrition': {'impactFactor': 7.324, 'quartile': 'Q2'},
    'European Journal of Clinical Nutrition': {'impactFactor': 3.614, 'quartile': 'Q2'},
    'Obesity Surgery': {'impactFactor': 3.895, 'quartile': 'Q2'},
    'Journal of Diabetes Research': {'impactFactor': 4.297, 'quartile': 'Q2'},
    'PLoS One': {'impactFactor': 3.752, 'quartile': 'Q2'},
    'Endocrine': {'impactFactor': 3.235, 'quartile': 'Q3'},
    'Hormone and Metabolic Research': {'impactFactor': 2.734, 'quartile': 'Q3'},
    'Journal of Clinical Endocrinology & Metabolism': {'impactFactor': 6.055, 'quartile': 'Q1'},
    'Diabetes & Metabolism': {'impactFactor': 4.579, 'quartile': 'Q2'},
    'Nutrition & Metabolism': {'impactFactor': 3.211, 'quartile': 'Q3'},
    'BMC Endocrine Disorders': {'impactFactor': 2.763, 'quartile': 'Q3'},
    'Saudi Medical Journal': {'impactFactor': 1.658, 'quartile': 'Q4'},
    'Annals of Saudi Medicine': {'impactFactor': 1.836, 'quartile': 'Q4'},
    'International Journal of Medical Sciences': {'impactFactor': 4.239, 'quartile': 'Q2'},
    'Medicine': {'impactFactor': 1.817, 'quartile': 'Q4'},
    'Journal of King Saud University - Science': {'impactFactor': 3.829, 'quartile': 'Q2'},
    'Saudi Journal of Biological Sciences': {'impactFactor': 4.562, 'quartile': 'Q2'}
}

app = Flask(__name__)

def fetch_publications():
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    
    while True:
        try:
            print(f"[{datetime.now()}] Fetching publications for {AUTHOR_NAME}...")
            
            # Step 1: Search for PMIDs
            search_url = f"{base_url}esearch.fcgi?db=pubmed&term={requests.utils.quote(AUTHOR_NAME)}[Author]&retmax=200&retmode=json&api_key={API_KEY}"
            res = requests.get(search_url)
            data = res.json()
            pmids = data["esearchresult"]["idlist"]
            
            if not pmids:
                print("⚠️ No publications found.")
                time.sleep(12 * 60 * 60)  # Wait 12h
                continue
            
            print(f"✅ Found {len(pmids)} PMIDs")
            
            # Step 2: Fetch full records
            id_str = ",".join(pmids)
            fetch_url = f"{base_url}efetch.fcgi?db=pubmed&id={id_str}&retmode=json&email={EMAIL}&tool=AcademicDashboard&api_key={API_KEY}"
            res = requests.get(fetch_url)
            pub_data = res.json()

            rows = []
            articles = pub_data.get("result", {}).get("uids", {})
            for uid in pmids:
                article = pub_data["result"].get(uid, {})
                medline = article.get("medlinecitation", {})
                art = medline.get("article", {})
                
                title = art.get("articletitle", "Unknown Title")
                year = art.get("publicationdate", {}).get("year", "Unknown")
                journal = art.get("journal", {}).get("title", "Unknown Journal")
                authors = "; ".join([f"{a.get('lastname', '')} {a.get('forename', '')}".strip() 
                                     for a in art.get("authorlist", {}).get("author", []) if a.get('lastname')])
                
                pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
                
                meta = JOURNAL_METADATA.get(journal, {'impactFactor': 2.5, 'quartile': 'Q3'})
                
                rows.append([
                    title,
                    int(year) if year.isdigit() else 0,
                    journal,
                    authors,
                    meta['quartile'],
                    meta['impactFactor'],
                    uid,
                    pubmed_url
                ])

            # Sort by year descending
            rows.sort(key=lambda x: x[1], reverse=True)

            # Update Google Sheet
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_FILE, scope)
            client = gspread.authorize(creds)
            sheet = client.open_by_key(SHEET_ID).sheet1

            # Clear existing data (keep header row)
            sheet.clear()
            sheet.append_row(["Title", "Year", "Journal", "Authors", "Quartile", "Impact Factor", "PMID", "PubmedURL"])
            for row in rows:
                sheet.append_row(row)

            print(f"✅ Updated {len(rows)} publications to Google Sheet.")

        except Exception as e:
            print(f"❌ Error: {e}")

        # Wait 12 hours before next fetch
        time.sleep(12 * 60 * 60)

@app.route('/health')
def health():
    return jsonify({"status": "ok", "message": "PubMed updater is running"}), 200

if __name__ == "__main__":
    # Start background thread for fetching publications
    thread = threading.Thread(target=fetch_publications, daemon=True)
    thread.start()

    # Start Flask server on the port Render provides
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 Starting Flask server on port {port}")
    app.run(host="0.0.0.0", port=port)
