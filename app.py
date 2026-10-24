import streamlit as st
import pdfplumber
import re
import datetime
import calendar
from fpdf import FPDF

# --- HILFSFUNKTION: MONATSENDE BERECHNEN ---
def ermittle_letzten_tag(monat_str):
    monate = {
        "Januar": 1, "Februar": 2, "März": 3, "Maerz": 3, "April": 4, 
        "Mai": 5, "Juni": 6, "Juli": 7, "August": 8, "September": 9, 
        "Oktober": 10, "November": 11, "Dezember": 12
    }
    try:
        teile = monat_str.strip().split()
        monat_zahl = monate.get(teile[0], datetime.datetime.now().month)
        jahr = int(teile[1])
        letzter_tag = calendar.monthrange(jahr, monat_zahl)[1]
        return f"{letzter_tag:02d}.{monat_zahl:02d}.{jahr}"
    except:
        return datetime.datetime.now().strftime("%d.%m.%Y")

# --- 1. DATENEXTRAKTION MIT LADEN-ERKENNUNG ---
# --- 1. DATENEXTRAKTION MIT BANK-FILTER ---
def extrahiere_daten(pdf_bytes):
    alle_mitarbeiter = []
    with pdfplumber.open(pdf_bytes) as pdf:
        for seite in pdf.pages:
            text = seite.extract_text()
            if not text:
                continue
            
            # 1. Prüfen, ob es wirklich eine Lohnabrechnung ist
            betrag_match = re.search(r"Netto-Bezüge/Netto-Abzüge\s+([\d\.,]+)", text)
            if not betrag_match:
                continue 
            
            # 2. NEU: Prüfen, ob es eine Banküberweisung ist (IBAN vorhanden)
            # Sucht nach "Konto DE" gefolgt von Zahlen
            if re.search(r"Konto\s+DE\d{2}", text):
                continue # Überspringt diese Seite, da keine Barquittung nötig ist!
                
            betrag = betrag_match.group(1)
                
            monat_match = re.search(r"für\s+([A-Za-zäöüÄÖÜ]+\s+\d{4})", text)
            monat = monat_match.group(1) if monat_match else "Unbekannt"
            
            # Automatische Ladenerkennung
            laden = "Salon Adam"
            if re.search(r"onarch|Karl-Mar", text, re.IGNORECASE):
                laden = "Monarch Hair Salon"

            name, strasse, plz_ort = "Unbekannt", "", ""
            zeilen = text.split('\n')
            for i, zeile in enumerate(zeilen):
                if re.search(r"^\d{5}\s+[A-Za-zäöüÄÖÜß]", zeile.strip()): 
                    plz_ort = zeile.strip()
                    strasse = zeilen[i-1].strip()
                    name = zeilen[i-2].strip()
                    break
            
            if name != "Unbekannt":
                alle_mitarbeiter.append({
                    "name": name, "strasse": strasse, "plz_ort": plz_ort, 
                    "monat": monat, "betrag": betrag, "laden": laden
                })
                
    return alle_mitarbeiter

# --- 2. SAMMEL-PDF-GENERATOR ---
def erstelle_sammel_quittung(mitarbeiter_liste, ausgabe_pfad="quittungen_fertig.pdf"):
    pdf = FPDF()
    
    for m in mitarbeiter_liste:
        pdf.add_page()
        zahlungsdatum = ermittle_letzten_tag(m["monat"])
        
        # Flexibler Arbeitgeber Block
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 5, "Arbeitgeber", ln=True)
        pdf.set_font("helvetica", "", 11)
        
        if m["laden"] == "Monarch Hair Salon":
            pdf.cell(0, 5, "Monarch Hair Salon", ln=True)
            pdf.cell(0, 5, "Karl-Marx-Straße 7", ln=True)
            pdf.cell(0, 5, "12043 Berlin", ln=True)
        else:
            pdf.cell(0, 5, "Shadi Muhsen", ln=True)
            pdf.cell(0, 5, "Salon Adam", ln=True)
            pdf.cell(0, 5, "Sonnenallee 42", ln=True)
            pdf.cell(0, 5, "12045 Berlin", ln=True)
            
        pdf.ln(8)
        
        # Arbeitnehmer Block
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 5, "Arbeitnehmer", ln=True)
        pdf.set_font("helvetica", "", 11)
        pdf.cell(0, 5, m["name"], ln=True)
        pdf.cell(0, 5, m["strasse"], ln=True)
        pdf.cell(0, 5, m["plz_ort"], ln=True)
        pdf.ln(15)
        
        # Überschrift
        pdf.set_font("helvetica", "B", 16)
        pdf.cell(0, 10, "QUITTUNG", ln=True)
        pdf.ln(5)
        
        # Quittungstext
        pdf.set_font("helvetica", "", 11)
        text = f"Hiermit bestätige ich, {m['name']}, dass ich meinen Lohn für den Monat {m['monat']} in Höhe von {m['betrag']} EUR vollständig in bar erhalten habe."
        text = text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
        pdf.multi_cell(0, 6, text)
        pdf.ln(10)
        
        # Zahlungsdetails
        pdf.cell(40, 6, "Zahlungsdatum:", border=0)
        pdf.cell(0, 6, zahlungsdatum, border=0, ln=True)
        pdf.cell(40, 6, "Zahlungsart:", border=0)
        pdf.cell(0, 6, "Barzahlung", border=0, ln=True)
        pdf.ln(15)
        
        # Unterschrift Block
        pdf.cell(0, 6, f"Berlin, den {zahlungsdatum}", ln=True)
        pdf.ln(15)
        pdf.cell(80, 0, "", border="T", ln=True)
        pdf.ln(2)
        pdf.cell(0, 6, m["name"], ln=True)
        pdf.cell(0, 6, "Unterschrift Arbeitnehmer / Empfangsbestätigung", ln=True)
        
    pdf.output(ausgabe_pfad)
    return ausgabe_pfad

# --- 3. STREAMLIT APP ---
st.set_page_config(page_title="Lohn-Quittungen", page_icon="📄")
st.title("📄 Automatischer Quittungsgenerator")

hochgeladene_datei = st.file_uploader("Abrechnung(en) als PDF auswählen", type=["pdf"])

if hochgeladene_datei is not None:
    if st.button("Quittungen generieren"):
        with st.spinner("Verarbeite Dokument..."):
            mitarbeiter_liste = extrahiere_daten(hochgeladene_datei)
            
            if not mitarbeiter_liste:
                st.error("Keine gültigen Abrechnungsdaten gefunden.")
            else:
                st.success(f"{len(mitarbeiter_liste)} Abrechnung(en) gefunden!")
                
                pdf_pfad = erstelle_sammel_quittung(mitarbeiter_liste)
                
                # Dynamischer Dateiname anhand des Ladens und Monats
                laden_fuer_dateiname = mitarbeiter_liste[0]["laden"].replace(" ", "_")
                monat_fuer_dateiname = mitarbeiter_liste[0]["monat"].replace(" ", "_")
                dateiname = f"Quittungen_{laden_fuer_dateiname}_{monat_fuer_dateiname}.pdf"
                
                with open(pdf_pfad, "rb") as pdf_file:
                    st.download_button(
                        label=f"📥 Alle {len(mitarbeiter_liste)} Quittungen herunterladen",
                        data=pdf_file,
                        file_name=dateiname,
                        mime="application/pdf"
                    )