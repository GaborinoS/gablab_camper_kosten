from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime
import json
import os

app = Flask(__name__)

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

# Template für die Hauptseite
@app.route('/templates/index.html')
def get_template():
    return '''
<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Camper Kosten-Tracker</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f8f9fa;
        }

        .navbar-brand {
            font-weight: bold;
            font-size: 1.5rem;
        }

        .card {
            transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
            border: none;
            border-radius: 10px;
        }

        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1) !important;
        }

        .display-4 {
            font-weight: 300;
            color: #0d6efd;
        }

        .lead {
            color: #6c757d;
        }

        .chart-container {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }

        .btn-primary {
            background-color: #0d6efd;
            border-color: #0d6efd;
            transition: all 0.3s ease;
        }

        .btn-primary:hover {
            background-color: #0b5ed7;
            border-color: #0a58ca;
            transform: translateY(-1px);
        }

        .form-control:focus, .form-select:focus {
            border-color: #86b7fe;
            box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
        }

        .stat-card {
            text-align: center;
            padding: 1.5rem;
        }

        .stat-number {
            font-size: 2.2em;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .stat-label {
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .schuld-card {
            background: linear-gradient(135deg, #dc3545, #c82333);
            color: white;
        }

        .ausgabe-item {
            border-bottom: 1px solid #eee;
            padding: 15px 0;
        }

        .ausgabe-item:last-child {
            border-bottom: none;
        }

        .kategorie-badge {
            background: #0d6efd;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
        }

        .anteil-controls {
            background: #e9ecef;
            padding: 15px;
            border-radius: 8px;
            margin-top: 15px;
        }

        .anteil-slider {
            width: 100%;
        }

        .anteil-display {
            text-align: center;
            margin-top: 10px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-4">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-rv me-2"></i>
                Camper Kosten-Tracker
            </a>
        </div>
    </nav>

    <div class="container">
        <!-- Header -->
        <div class="text-center mb-5">
            <h1 class="display-4">Camper Ausbau Budget</h1>
            <p class="lead">Gabsi & Sabi's Ausgaben-Verwaltung</p>
        </div>
        
        <!-- Statistiken -->
        <div class="row mb-4">
            <div class="col-md-3 mb-3">
                <div class="card stat-card">
                    <div class="card-body">
                        <div class="stat-number text-primary">€{{ "%.2f"|format(schulden.gesamt_ausgaben) }}</div>
                        <div class="stat-label">Gesamt Ausgaben</div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card stat-card">
                    <div class="card-body">
                        <div class="stat-number text-info">€{{ "%.2f"|format(schulden.gabsi_bezahlt) }}</div>
                        <div class="stat-label">Gabsi bezahlt</div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card stat-card">
                    <div class="card-body">
                        <div class="stat-number text-warning">€{{ "%.2f"|format(schulden.sabi_bezahlt) }}</div>
                        <div class="stat-label">Sabi bezahlt</div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-3 mb-3">
                <div class="card stat-card schuld-card">
                    <div class="card-body">
                        <div class="stat-number">€{{ "%.2f"|format(schulden.schuld.betrag) }}</div>
                        <div class="stat-label">{{ schulden.schuld.schuldner }} schuldet {{ schulden.schuld.glaeubiger }}</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Eingabeformular -->
        <div class="card mb-4">
            <div class="card-header">
                <h3 class="mb-0"><i class="fas fa-plus-circle me-2"></i>Neue Ausgabe hinzufügen</h3>
            </div>
            <div class="card-body">
                <form method="POST" action="/neue_ausgabe">
                    <div class="row">
                        <div class="col-md-6 mb-3">
                            <label for="datum" class="form-label">Datum:</label>
                            <input type="date" class="form-control" id="datum" name="datum" required value="{{ heute }}">
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <label for="bezahlt_von" class="form-label">Bezahlt von:</label>
                            <select class="form-select" id="bezahlt_von" name="bezahlt_von" required>
                                <option value="">Wählen...</option>
                                <option value="Gabsi">Gabsi</option>
                                <option value="Sabi">Sabi</option>
                            </select>
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <label for="betrag" class="form-label">Betrag (€):</label>
                            <input type="number" step="0.01" class="form-control" id="betrag" name="betrag" required placeholder="0.00">
                        </div>
                        
                        <div class="col-md-6 mb-3">
                            <label for="kategorie" class="form-label">Kategorie:</label>
                            <select class="form-select" id="kategorie" name="kategorie" required>
                                <option value="">Kategorie wählen...</option>
                                {% for kat in kategorie_liste %}
                                <option value="{{ kat }}">{{ kat }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        
                        <div class="col-12 mb-3">
                            <label for="beschreibung" class="form-label">Beschreibung:</label>
                            <textarea class="form-control" id="beschreibung" name="beschreibung" rows="3" required placeholder="Was wurde gekauft?"></textarea>
                        </div>
                        
                        <!-- Anpassbare Aufteilung -->
                        <div class="col-12 mb-3">
                            <div class="anteil-controls">
                                <label class="form-label">Kostenaufteilung anpassen:</label>
                                <div class="row">
                                    <div class="col-md-6">
                                        <label for="gabsi_anteil" class="form-label">Gabsi Anteil (%):</label>
                                        <input type="range" class="form-range anteil-slider" id="gabsi_anteil" name="gabsi_anteil" 
                                               min="0" max="100" value="{{ gabsi_default }}" oninput="updateAnteile()">
                                        <div class="anteil-display" id="gabsi_display">{{ gabsi_default }}%</div>
                                    </div>
                                    <div class="col-md-6">
                                        <label for="sabi_anteil" class="form-label">Sabi Anteil (%):</label>
                                        <input type="range" class="form-range anteil-slider" id="sabi_anteil" name="sabi_anteil" 
                                               min="0" max="100" value="{{ sabi_default }}" oninput="updateAnteile()">
                                        <div class="anteil-display" id="sabi_display">{{ sabi_default }}%</div>
                                    </div>
                                </div>
                                <small class="text-muted">Standard: Gabsi 60%, Sabi 40%</small>
                            </div>
                        </div>
                        
                        <div class="col-12 text-center">
                            <button type="submit" class="btn btn-primary btn-lg">
                                <i class="fas fa-save me-2"></i>Ausgabe speichern
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="row mb-4">
            <div class="col-md-6 mb-3">
                <div class="card chart-container">
                    <div class="card-header">
                        <h5 class="mb-0">Ausgaben nach Kategorien</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="kategorienChart"></canvas>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6 mb-3">
                <div class="card chart-container">
                    <div class="card-header">
                        <h5 class="mb-0">Bezahlt von</h5>
                    </div>
                    <div class="card-body">
                        <canvas id="personenChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Ausgabenliste -->
        <div class="card">
            <div class="card-header">
                <h3 class="mb-0">
                    <i class="fas fa-list me-2"></i>
                    Alle Ausgaben ({{ ausgaben|length }} Einträge)
                </h3>
            </div>
            <div class="card-body">
                {% if ausgaben %}
                    {% for ausgabe in ausgaben|reverse %}
                    <div class="ausgabe-item">
                        <div class="row align-items-center">
                            <div class="col-md-2">
                                <small class="text-muted">{{ ausgabe.datum }}</small>
                            </div>
                            <div class="col-md-4">
                                <strong>{{ ausgabe.beschreibung }}</strong><br>
                                <small class="text-muted">von {{ ausgabe.bezahlt_von }}</small>
                                {% if ausgabe.gabsi_anteil != gabsi_default or ausgabe.sabi_anteil != sabi_default %}
                                <br><small class="text-info">Aufteilung: {{ ausgabe.gabsi_anteil }}% / {{ ausgabe.sabi_anteil }}%</small>
                                {% endif %}
                            </div>
                            <div class="col-md-2">
                                <span class="kategorie-badge">{{ ausgabe.kategorie }}</span>
                            </div>
                            <div class="col-md-2">
                                <strong class="text-success">€{{ "%.2f"|format(ausgabe.betrag) }}</strong>
                            </div>
                            <div class="col-md-2 text-end">
                                <button class="btn btn-outline-danger btn-sm" 
                                        onclick="if(confirm('Ausgabe löschen?')) window.location.href='/loeschen/{{ ausgabe.id }}'">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="text-center py-5">
                        <i class="fas fa-inbox fa-3x text-muted mb-3"></i>
                        <p class="text-muted">Noch keine Ausgaben vorhanden. Fügt eure erste Ausgabe hinzu!</p>
                    </div>
                {% endif %}
            </div>
        </div>
    </div>
    
    <footer class="mt-5 py-4 bg-light border-top">
        <div class="container text-center">
            <p class="text-muted mb-0">Camper Kosten-Tracker - Gabsi & Sabi</p>
        </div>
    </footer>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/5.3.0/js/bootstrap.bundle.min.js"></script>
    <script>
        // Aufteilungs-Slider synchronisieren
        function updateAnteile() {
            const gabsiSlider = document.getElementById('gabsi_anteil');
            const sabiSlider = document.getElementById('sabi_anteil');
            const gabsiDisplay = document.getElementById('gabsi_display');
            const sabiDisplay = document.getElementById('sabi_display');
            
            const gabsiWert = parseInt(gabsiSlider.value);
            const sabiWert = 100 - gabsiWert;
            
            sabiSlider.value = sabiWert;
            gabsiDisplay.textContent = gabsiWert + '%';
            sabiDisplay.textContent = sabiWert + '%';
        }
        
        // Sabi-Slider umgekehrt synchronisieren
        document.getElementById('sabi_anteil').addEventListener('input', function() {
            const sabiWert = parseInt(this.value);
            const gabsiWert = 100 - sabiWert;
            
            document.getElementById('gabsi_anteil').value = gabsiWert;
            document.getElementById('gabsi_display').textContent = gabsiWert + '%';
            document.getElementById('sabi_display').textContent = sabiWert + '%';
        });
        
        // Charts laden
        fetch('/api/chart_data')
            .then(response => response.json())
            .then(data => {
                // Kategorien Chart
                const kategorienCtx = document.getElementById('kategorienChart').getContext('2d');
                new Chart(kategorienCtx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(data.kategorien),
                        datasets: [{
                            data: Object.values(data.kategorien),
                            backgroundColor: [
                                '#0d6efd', '#6f42c1', '#d63384', '#dc3545', 
                                '#fd7e14', '#ffc107', '#198754', '#20c997',
                                '#0dcaf0', '#6c757d', '#f8f9fa', '#212529'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'bottom'
                            }
                        }
                    }
                });
                
                // Personen Chart
                const personenCtx = document.getElementById('personenChart').getContext('2d');
                new Chart(personenCtx, {
                    type: 'pie',
                    data: {
                        labels: Object.keys(data.bezahlt_von),
                        datasets: [{
                            data: Object.values(data.bezahlt_von),
                            backgroundColor: ['#0d6efd', '#6f42c1']
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'bottom'
                            }
                        }
                    }
                });
            });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    # Template-Ordner erstellen falls nicht vorhanden
    os.makedirs('templates', exist_ok=True)
    
    # Template-Datei schreiben
    template_content = get_template()
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(template_content)
    
    print("Camper Kosten-Tracker wird gestartet...")
    print("App läuft auf: http://localhost:5000")
    print("Drücke Ctrl+C zum Beenden")
    
    app.run(debug=True, host='0.0.0.0', port=5000)