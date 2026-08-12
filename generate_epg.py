import datetime
import gzip
import json
import re
import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configurazione
NUM_DAYS = 3  # Scarica oggi, domani e dopodomani
BASE_URL = "https://guidatv.lazzy.live/dati/giorni/"

def clean_text(text):
    if not text:
        return ""
    return str(text).strip()

def format_xmltv_date(date_str):
    """
    Converte date ISO/timestamp in formato XMLTV standard (YYYYMMDDHHMMSS +0200)
    """
    if not date_str:
        return ""
    try:
        # Pulisce eventuali millisecondi o formati non standard
        dt = datetime.datetime.fromisoformat(str(date_str).replace('Z', '+00:00'))
        return dt.strftime("%Y%m%d%H%M%S +0200")
    except Exception:
        return ""

def main():
    root = ET.Element("tv", {"generator-info-name": "Custom Lazzy EPG Generator"})
    channels_added = set()

    today = datetime.date.today()

    for i in range(NUM_DAYS):
        day_date = today + datetime.timedelta(days=i)
        day_str = day_date.strftime("%Y-%m-%d")
        url = f"{BASE_URL}{day_str}.json"
        
        print(f"--> Scaricamento guida per il giorno {day_str}...")
        try:
            res = requests.get(url, timeout=15)
            if res.status_code != 200:
                print(f"    Attenzione: HTTP status {res.status_code} per {url}")
                continue
            data = res.json()
        except Exception as e:
            print(f"    Errore durante il download o parsing di {url}: {e}")
            continue

        # Estrazione canali e programmi dalla struttura JSON
        canali = data.get("canali", []) if isinstance(data, dict) else data

        for ch in canali:
            ch_id = str(ch.get("id") or ch.get("slug") or ch.get("nome", "")).lower().replace(" ", "")
            ch_name = clean_text(ch.get("nome", ch_id))
            ch_logo = clean_text(ch.get("logo", ""))

            if not ch_id:
                continue

            # Aggiunge il canale al nodo XML (solo una volta)
            if ch_id not in channels_added:
                channel_elem = ET.SubElement(root, "channel", id=ch_id)
                display_name = ET.SubElement(channel_elem, "display-name")
                display_name.text = ch_name
                if ch_logo:
                    ET.SubElement(channel_elem, "icon", src=ch_logo)
                channels_added.add(ch_id)

            # Aggiunge la lista dei programmi del canale
            for prog in ch.get("programmi", []):
                start = format_xmltv_date(prog.get("ora_inizio") or prog.get("inizio"))
                stop = format_xmltv_date(prog.get("ora_fine") or prog.get("fine"))
                
                if not start:
                    continue

                prog_elem = ET.SubElement(root, "programme", channel=ch_id)
                prog_elem.set("start", start)
                if stop:
                    prog_elem.set("stop", stop)

                title_text = clean_text(prog.get("titolo") or prog.get("title") or "N/D")
                title = ET.SubElement(prog_elem, "title", lang="it")
                title.text = title_text

                desc_text = clean_text(prog.get("descrizione") or prog.get("description"))
                if desc_text:
                    desc = ET.SubElement(prog_elem, "desc", lang="it")
                    desc.text = desc_text

                cat_text = clean_text(prog.get("categoria") or prog.get("category"))
                if cat_text:
                    cat = ET.SubElement(prog_elem, "category", lang="it")
                    cat.text = cat_text

    # Formatting XML
    xml_str = minidom.parseString(ET.tostring(root, encoding="utf-8")).toprettyxml(indent="  ")

    # Salvataggio file epg.xml
    with open("epg.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)

    # Salvataggio file compresso epg.xml.gz
    with open("epg.xml", "rb") as f_in:
        with gzip.open("epg.xml.gz", "wb") as f_out:
            f_out.writelines(f_in)

    print("✅ EPG generata e compressa (epg.xml.gz) con successo!")

if __name__ == "__main__":
    main()
