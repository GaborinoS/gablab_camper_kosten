from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import json
import os

# Flask-App mit Subpfad konfigurieren
app = Flask(__name__)

# Konfiguration für Subpfad
class ReverseProxied(object):
    def __init__(self, app, script_name=None, scheme=None, server=None):
        self.app = app
        self.script_name = script_name
        self.scheme = scheme
        self.server = server

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '') or self.script_name
        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]
        scheme = environ.get('HTTP_X_SCHEME', '') or self.scheme
        if scheme:
            environ['wsgi.url_scheme'] = scheme
        server = environ.get('HTTP_X_FORWARDED_SERVER', '') or self.server
        if server:
            environ['SERVER_NAME'] = server
        return self.app(environ, start_response)

# Wrapper anwenden
app.wsgi_app = ReverseProxied(app.wsgi_app, script_name='/tracker')

# Standard-Konfiguration
GABSI_ANTEIL_DEFAULT = 60  # 60%
SABI_ANTEIL_DEFAULT = 40   # 40%

# Vordefinierte Kategorien
KATEGORIEN = [
    'Autoteile',
    'Bett & Matratze', 
    'Küche & Kochen',
    'Elektrik & Solar',
    'Werkzeug',
    'Isolation & Dämmung',
    'Möbel & Stauraum',
    'Wasser & Sanitär',
    'Heizung',
    'Dekoration',
    'Sicherheit',
    'Sonstiges',
    'Tank',
    'Putzmittel',
    'Baumaterial'
]

# Datei für persistente Speicherung
DATA_FILE = 'ausgaben.json'

def load_data():
    """Lädt Ausgaben aus der JSON-Datei"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_data(ausgaben):
    """Speichert Ausgaben in die JSON-Datei"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(ausgaben, f, ensure_ascii=False, indent=2)

def berechne_schulden(ausgaben):
    """Berechnet wer wem wieviel schuldet basierend auf individuellen Aufteilungen"""
    gabsi_bezahlt = 0
    sabi_bezahlt = 0
    gabsi_soll = 0
    sabi_soll = 0
    
    for ausgabe in ausgaben:
        betrag = ausgabe['betrag']
        gabsi_anteil = ausgabe.get('gabsi_anteil', GABSI_ANTEIL_DEFAULT) / 100
        sabi_anteil = ausgabe.get('sabi_anteil', SABI_ANTEIL_DEFAULT) / 100
        
        # Wer hat bezahlt
        if ausgabe['bezahlt_von'] == 'Gabsi':
            gabsi_bezahlt += betrag
        else:
            sabi_bezahlt += betrag
            
        # Wer soll wieviel tragen
        gabsi_soll += betrag * gabsi_anteil
        sabi_soll += betrag * sabi_anteil
    
    gesamt_ausgaben = gabsi_bezahlt + sabi_bezahlt
    gabsi_bilanz = gabsi_bezahlt - gabsi_soll
    sabi_bilanz = sabi_bezahlt - sabi_soll
    
    if gabsi_bilanz > 0:
        schuld_info = {
            'schuldner': 'Sabi',
            'glaeubiger': 'Gabsi', 
            'betrag': abs(gabsi_bilanz)
        }
    else:
        schuld_info = {
            'schuldner': 'Gabsi',
            'glaeubiger': 'Sabi',
            'betrag': abs(sabi_bilanz)
        }
    
    return {
        'gabsi_bezahlt': gabsi_bezahlt,
        'sabi_bezahlt': sabi_bezahlt,
        'gesamt_ausgaben': gesamt_ausgaben,
        'gabsi_soll': gabsi_soll,
        'sabi_soll': sabi_soll,
        'gabsi_bilanz': gabsi_bilanz,
        'sabi_bilanz': sabi_bilanz,
        'schuld': schuld_info
    }

@app.route('/')
def index():
    """Hauptseite mit Übersicht"""
    ausgaben = load_data()
    schulden = berechne_schulden(ausgaben)
    
    # Kategorien für Charts
    kategorien = {}
    for ausgabe in ausgaben:
        kat = ausgabe['kategorie']
        if kat not in kategorien:
            kategorien[kat] = 0
        kategorien[kat] += ausgabe['betrag']
    
    # Heutiges Datum für Formular
    heute = datetime.now().strftime('%Y-%m-%d')
    
    return render_template('index.html', 
                         ausgaben=ausgaben, 
                         schulden=schulden,
                         kategorien=kategorien,
                         kategorie_liste=KATEGORIEN,
                         heute=heute,
                         gabsi_default=GABSI_ANTEIL_DEFAULT,
                         sabi_default=SABI_ANTEIL_DEFAULT)

@app.route('/neue_ausgabe', methods=['POST'])
def neue_ausgabe():
    """Neue Ausgabe hinzufügen"""
    ausgaben = load_data()
    
    # Neue ID generieren
    max_id = max([a['id'] for a in ausgaben], default=0)
    
    neue_ausgabe = {
        'id': max_id + 1,
        'datum': request.form['datum'],
        'beschreibung': request.form['beschreibung'],
        'betrag': float(request.form['betrag']),
        'kategorie': request.form['kategorie'],
        'bezahlt_von': request.form['bezahlt_von'],
        'gabsi_anteil': int(request.form.get('gabsi_anteil', GABSI_ANTEIL_DEFAULT)),
        'sabi_anteil': int(request.form.get('sabi_anteil', SABI_ANTEIL_DEFAULT))
    }
    
    ausgaben.append(neue_ausgabe)
    save_data(ausgaben)
    
    return redirect(url_for('index'))

@app.route('/loeschen/<int:ausgabe_id>')
def loeschen(ausgabe_id):
    """Ausgabe löschen"""
    ausgaben = load_data()
    ausgaben = [a for a in ausgaben if a['id'] != ausgabe_id]
    save_data(ausgaben)
    return redirect(url_for('index'))

@app.route('/api/chart_data')
def chart_data():
    """API für Chart-Daten"""
    ausgaben = load_data()
    schulden = berechne_schulden(ausgaben)
    
    # Kategorien-Daten
    kategorien = {}
    for ausgabe in ausgaben:
        kat = ausgabe['kategorie']
        if kat not in kategorien:
            kategorien[kat] = 0
        kategorien[kat] += ausgabe['betrag']
    
    # Monatliche Ausgaben
    monate = {}
    for ausgabe in ausgaben:
        monat = ausgabe['datum'][:7]  # YYYY-MM
        if monat not in monate:
            monate[monat] = 0
        monate[monat] += ausgabe['betrag']
    
    return jsonify({
        'kategorien': kategorien,
        'monate': monate,
        'bezahlt_von': {
            'Gabsi': schulden['gabsi_bezahlt'],
            'Sabi': schulden['sabi_bezahlt']
        }
    })

if __name__ == '__main__':
    # Template-Ordner erstellen falls nicht vorhanden
    os.makedirs('templates', exist_ok=True)
    
    # Template-Datei ist bereits vorhanden - wird nicht überschrieben
    print("Camper Kosten-Tracker wird gestartet...")
    print("App läuft auf: http://localhost:2503")
    print("Über nginx erreichbar unter: https://gab-lab.at/tracker")
    print("Drücke Ctrl+C zum Beenden")
    
    app.run(debug=False, host='0.0.0.0', port=2503)