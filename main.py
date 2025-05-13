import pandas as pd

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import SpanSelector  
import mplcursors

import tkinter as tk
from tkinter import filedialog

from datetime import datetime
import os
import re
import sys

def extract_versuch_name(file_path):
    base_name = os.path.splitext(os.path.basename(file_path))[0]

    # Suche nach 'versuch' oder 'versuche' gefolgt von einer Zahl
    match = re.search(r'versuch[e]?\s*(\d+)', base_name, re.IGNORECASE)
    if match:
        return f"Versuch {match.group(1)}"
    else:
        return base_name  # Falls kein Match, originaler Name

# --- Schritt 1: CSV-Datei auswählen und laden ---
def load_csv():
    root = tk.Tk()
    root.withdraw()
    df_path = filedialog.askopenfilename(title="CSV-Datei auswählen", filetypes=[("CSV files", "*.csv")])
    if not df_path:
        print("Keine Datei ausgewählt.")
        return None, None
    df = pd.read_csv(df_path)
    print(f"{len(df)} Zeilen geladen aus: {df_path}")
    return df, df_path

# --- Schritt 2: XY-Plot anzeigen und Bereich markieren ---
def plot_and_select(df, x_col, y_cols, fig, ax):
    # speichere den alten Titel
    original_title = ax.get_title()

    ax.clear()  # Lösche den alten Plot, bevor ein neuer gezeichnet wird
    ax.set_title(original_title)
    ax.plot(df[x_col], df[y_cols], label=y_cols)
    ax.set_xlabel(x_col)
    # ax.set_ylabel(y_cols)
    
    ax.legend()
    # ax.legend(loc='upper right') 
    ax.set_xlim(df[x_col].min(), df[x_col].max())

    selected_data = []

    return selected_data

# --- Schritt 3: Exportiere markierten Bereich ---
def export_csv(data, original_path):
    if data.empty:
        print("Keine Daten zum Exportieren.")
        return
    
    # Basisname ohne Endung
    base_name = os.path.splitext(os.path.basename(original_path))[0]
    
    # Zeitstempel anhängen (bis Minute genau)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    
    # Neuer Dateiname
    new_filename = f"{base_name}_{timestamp}.csv"
    
    # Im selben Verzeichnis wie Originaldatei speichern
    export_dir = os.path.dirname(original_path)
    export_path = os.path.join(export_dir, new_filename)
    
    # Exportieren
    data.to_csv(export_path, index=False)
    print(f"Exportiert nach: {export_path}")

# --- Hauptfunktion mit Tkinter GUI ---
def main():
    selected_data = None
    df_path = None
    df = None
    x_col = None
    y_cols = None
    x_min = None
    x_max= None

    cursor = None  # globale Referenz
    span = None    # globale Referenz

    def switch_mode():
        nonlocal cursor, span

        # Entferne beide
        if cursor:
            cursor.remove()
            cursor = None
        if span:
            span.disconnect_events()
            span = None

        if edit_mode.get():
            # Bearbeiten: nur SpanSelector
            span = SpanSelector(ax, onselect, 'horizontal', useblit=True,
                                props=dict(alpha=0.5, facecolor='red'))
            print("Modus: Bearbeiten (Bereichsauswahl)")
        else:
            # Anzeigen: nur Cursor
            import mplcursors
            cursor = mplcursors.cursor(ax, hover=True)
            cursor.connect("add", lambda sel: sel.annotation.set_text(
                f"x = {sel.target[0]:.2f} s\ny = {sel.target[1]:.2f}"
            ))
            print("Modus: Anzeigen (Interaktiver Cursor)")

        fig.canvas.draw_idle()

    def on_closing():
        print("Fenster wird geschlossen. Beende das Skript...")
        sys.exit()  # Beendet das Skript

    root = tk.Tk()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.title("CSV Editor & Plotter")

    pwm_visible = tk.BooleanVar(value=True)  # Anfangszustand: PWM anzeigen
    edit_mode = tk.BooleanVar(value=True)  # True = Bearbeiten, False = Anzeige
    
    # Aufteilung in zwei Bereiche
    left_frame = tk.Frame(root, width=250, height=500)
    left_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
    
    right_frame = tk.Frame(root, width=500, height=500)
    right_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
    
    # Konfigurieren des Layouts
    root.grid_rowconfigure(0, weight=1)
    root.grid_columnconfigure(1, weight=1)
    
    # Buttons und Labels auf der linken Seite
    load_button = tk.Button(left_frame, text="CSV Laden", command=lambda: load_data())
    load_button.pack(pady=10)

    csv_export_button = tk.Button(left_frame, text="CSV exportieren", command=lambda: export_data())
    csv_export_button.pack(pady=10)

    svg_export_button = tk.Button(left_frame, text="SVG exportieren", command=lambda: export_plot())
    svg_export_button.pack(pady=10)
    
    info_label = tk.Label(left_frame, text="Warten auf CSV-Datei...")
    info_label.pack(pady=10)

    rezero_button = tk.Button(left_frame, text="X-Achsenstart nullen", command=lambda: rezero())
    rezero_button.pack(pady=10)

    reset_button = tk.Button(left_frame, text="Auswahl zurücksetzen", command=lambda: reset_selection())
    reset_button.pack(pady=10)

    pwm_checkbox = tk.Checkbutton(left_frame, text="PWM anzeigen", variable=pwm_visible, command=lambda: update_plot())
    pwm_checkbox.pack(pady=5)

    ## Radiobutton Show-Edit-mode
    mode_frame = tk.LabelFrame(left_frame, text="Modus")
    mode_frame.pack(pady=10)

    edit_radio = tk.Radiobutton(mode_frame, text="Bearbeiten", variable=edit_mode, value=True, command=lambda: switch_mode())
    edit_radio.pack(anchor='w')

    view_radio = tk.Radiobutton(mode_frame, text="Anzeigen", variable=edit_mode, value=False, command=lambda: switch_mode())
    view_radio.pack(anchor='w')
    ## Radiobutton Show-Edit-mode ende
    
    # Matplotlib-Plot auf der rechten Seite
    fig, ax = plt.subplots(figsize=(6, 3))
    canvas = FigureCanvasTkAgg(fig, master=right_frame)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Interaktiver Cursor
    cursor = mplcursors.cursor(ax, hover=True)
    cursor.connect("add", lambda sel: sel.annotation.set_text(
        f"x = {sel.target[0]:.2f} s\ny = {sel.target[1]:.2f}"
    ))

    def reset_selection():
        onselect(df[x_col].min(), df[x_col].max())
        rezero()

    def onselect(xmin, xmax):
        nonlocal selected_data, x_col, df, x_min, x_max
        # Bereich filtern
        try:
            x_min = xmin
            x_max = xmax
            mask = (df[x_col] >= xmin) & (df[x_col] <= xmax)
            selected_data = df[mask]
            print(f"{len(selected_data)} Punkte im markierten Bereich.")
            ax.set_xlim(xmin, xmax)
            fig.canvas.draw()  # Zeichne den Plot nach der Auswahl neu
        except Exception as e:
            print(f"Fehler beim Auswählen: {e}")

    span = SpanSelector(ax, onselect, 'horizontal', useblit=True,
                    props=dict(alpha=0.5, facecolor='red'))
    
    

    def load_data():
        nonlocal df, df_path, selected_data, x_col, y_cols
        df, df_path = load_csv()
        if df is None:
            return
        info_label.config(text=f"Datei geladen: {df_path}")
        
        # Spalten anzeigen und Plot vorbereiten
        if 'Zeit [in ms]' in df.columns:
            df['Zeit [in ms]'] = df['Zeit [in ms]'] / 1000
            df.rename(columns={'Zeit [in ms]': 'Zeit [in s]'}, inplace=True)
            x_col = 'Zeit [in s]'
        elif 'Zeit [in s]' in df.columns:
            x_col = 'Zeit [in s]'
        else:
            x_col = input("Spaltenname für X-Achse: ")
        
        y_candidates = ['Temp1 [in °C]', 'Temp2 [in °C]', 'Temp3 [in °C]', 'PWM [0-255]']
        y_cols = [col for col in y_candidates if col in df.columns]
        
        if x_col not in df.columns or not y_cols:
            print("Ungültige Spaltennamen.")
            return
        
        selected_data = plot_and_select(df, x_col, y_cols, fig, ax)
        
        # setze den Titel des Plots nachdem eine Datei geladen wurde
        title = extract_versuch_name(df_path)
        ax.set_title(title)

        canvas.draw_idle()  # Aktualisiere den Canvas

    def update_plot():
        nonlocal df, x_col, y_cols
        if df is None or x_col is None:
            return
        # Wähle Y-Spalten abhängig von Checkbox
        y_candidates = ['Temp1 [in °C]', 'Temp2 [in °C]', 'Temp3 [in °C]']
        if pwm_visible.get():
            y_candidates.append('PWM [0-255]')
        y_cols = [col for col in y_candidates if col in df.columns]

        plot_and_select(df, x_col, y_cols, fig, ax)
        canvas.draw_idle()

    def export_data():
        if df is None or selected_data is None or selected_data.empty:
            print("Keine Daten zum Exportieren.")
            return
        export_csv(selected_data, df_path)
        info_label.config(text=f"CSV exportiert: {df_path}")

    def export_plot():
        if df is None:
            print("Kein Plot zum Exportieren.")
            return

        # Basisname ohne Endung
        base_name = os.path.splitext(os.path.basename(df_path))[0]

        # Zeitstempel
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")

        # Neuer Dateiname
        new_filename = f"{base_name}_{timestamp}.svg"

        # Exportpfad
        export_dir = os.path.dirname(df_path)
        export_path = os.path.join(export_dir, new_filename)

        # Plot speichern

        # Aktuelle (ursprüngliche) Größe speichern
        original_size = fig.get_size_inches()
        original_title = ax.get_title()

        # Temporäre feste Größe setzen
        fig.set_size_inches(6, 3)                                               # Plotexport Setting: Breite x Höhe in Zoll
        ax.set_title("")                                             # Plotexport Setting: lösche titel

        fig.savefig(export_path, format='svg', bbox_inches='tight')

        # Ursprüngliche Größe wiederherstellen
        fig.set_size_inches(original_size)
        ax.set_title(original_title)

        print(f"Plot exportiert als SVG: {export_path}")
        info_label.config(text=f"SVG exportiert: {export_path}")

    def rezero():
        nonlocal df, selected_data, x_col, y_cols, x_min
        if df is None or x_col is None:
            print("Keine Daten zum Nullen vorhanden.")
            return

        # Auswahl anpassen (falls vorhanden)
        if selected_data is not None and not selected_data.empty:
            selected_data[x_col] = selected_data[x_col] - x_min

        # Plot aktualisieren
        plot_and_select(selected_data, x_col, y_cols, fig, ax)
        canvas.draw_idle()

        print(f"Zeitachse genullt. Neuer Start bei {df[x_col].min()}.")

       

    root.mainloop()

if __name__ == "__main__":
    main()
