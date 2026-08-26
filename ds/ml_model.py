"""
ml_model.py — FrostAnalitic Modulo de Ciencia de Datos
Entrena 3 modelos ML, compara con el arbol de reglas,
genera graficas y guarda el mejor modelo.
Todo se guarda en ds/output/ relativo a este script.
"""
import os, pickle, warnings
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
warnings.filterwarnings('ignore')

from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix

# ── Rutas relativas (funciona en cualquier PC) ────────────────
BASE   = os.path.dirname(os.path.abspath(__file__))
CSV    = os.path.join(BASE, "dataset_diagnosticos.csv")
OUT    = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)

FALLA_NOMBRES = {
    1:"Fuga refrigerante", 2:"Capilar obstruido",  3:"Compresor defect.",
    4:"Relay/capacitor",   5:"Termostato",          6:"Vent. evaporador",
    7:"Vent. condensador", 8:"Condensador sucio",   9:"Drenaje obstruido",
   10:"Empaque puerta",   11:"Deshielo defect.",   12:"Tarjeta control",
   13:"Filtros sucios",   14:"Aislamiento",        15:"Sensor temperatura",
   16:"Resist. anti-vaho",17:"Falla electrica",    18:"Rodamientos"
}

print("=" * 55)
print("  FrostAnalitic — Modulo Ciencia de Datos")
print("=" * 55)

# ── 1. Cargar datos ───────────────────────────────────────────
if not os.path.exists(CSV):
    print(f"\nERROR: No se encontro {CSV}")
    print("Ejecuta primero:  python ds/simulate_data.py")
    raise SystemExit(1)

df = pd.read_csv(CSV)
print(f"\n Datos cargados: {len(df)} registros")
print(f"\nDistribucion por equipo:")
print(df["equipo"].value_counts().to_string())

prec_actual = df["fue_correcto"].mean() * 100
print(f"\nPrecision actual del arbol de reglas: {prec_actual:.1f}%")

# ── 2. Features ───────────────────────────────────────────────
le_eq   = LabelEncoder()
le_sint = LabelEncoder()
df["equipo_enc"]  = le_eq.fit_transform(df["equipo"])
df["sintoma_enc"] = le_sint.fit_transform(df["sintoma"])

X = df[["equipo_enc", "sintoma_enc", "probabilidad"]].values
y = df["falla_correcta_id"].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.25, random_state=42, stratify=y
)
print(f"\nTrain: {len(X_train)} | Test: {len(X_test)}")

# ── 3. Entrenar modelos ───────────────────────────────────────
modelos = {
    "Arbol de Decision": DecisionTreeClassifier(max_depth=8, random_state=42),
    "Random Forest":     RandomForestClassifier(n_estimators=100, random_state=42),
    "Naive Bayes":       GaussianNB(),
}

resultados = {}
print("\nEntrenando modelos...")
for nombre, modelo in modelos.items():
    modelo.fit(X_train, y_train)
    y_pred = modelo.predict(X_test)
    acc = accuracy_score(y_test, y_pred) * 100
    f1  = f1_score(y_test, y_pred, average="weighted", zero_division=0) * 100
    cv  = cross_val_score(modelo, X, y, cv=5, scoring="accuracy").mean() * 100
    resultados[nombre] = {"modelo": modelo, "acc": acc, "f1": f1, "cv": cv, "pred": y_pred}
    print(f"  {nombre:<22}  Acc={acc:.1f}%  F1={f1:.1f}%  CV={cv:.1f}%")

mejor_nombre = max(resultados, key=lambda k: resultados[k]["acc"])
mejor = resultados[mejor_nombre]
mejora = mejor["acc"] - prec_actual
print(f"\nMejor modelo: {mejor_nombre} ({mejor['acc']:.1f}%)")
print(f"Mejora vs arbol de reglas: +{mejora:.1f}%")

# Guardar modelo
with open(os.path.join(OUT, "frost_model.pkl"), "wb") as f:
    pickle.dump({"modelo": mejor["modelo"], "le_eq": le_eq,
                 "le_sint": le_sint, "nombre": mejor_nombre}, f)
print(f"\nModelo guardado: ds/output/frost_model.pkl")

# ── 4. Grafica 1 — Comparacion de modelos ────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
fig.patch.set_facecolor("#040608"); ax.set_facecolor("#080c10")
nombres = ["Arbol actual"] + list(resultados.keys())
accs    = [prec_actual]    + [resultados[k]["acc"] for k in resultados]
colores = ["#ffd700", "#00d4ff", "#00ff88", "#ff8800"]
bars = ax.bar(nombres, accs, color=colores, width=0.55, zorder=3)
ax.set_ylim(50, 105)
ax.set_ylabel("Precision (%)", color="#8aacbe", fontsize=11)
ax.set_title("Comparacion de Modelos — FrostAnalitic",
             color="#e8f0f8", fontsize=13, fontweight="bold", pad=14)
ax.tick_params(colors="#8aacbe"); ax.spines[:].set_color("#1e2a36")
ax.grid(axis="y", color="#141c24", zorder=0, linewidth=0.8)
for bar, val in zip(bars, accs):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.5,
            f"{val:.1f}%", ha="center", va="bottom",
            color="#e8f0f8", fontsize=10, fontweight="bold")
ax.axhline(prec_actual, color="#ffd700", linewidth=1, linestyle="--", alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "comparacion_modelos.png"),
            dpi=150, bbox_inches="tight", facecolor="#040608")
plt.close()
print("Grafica 1: comparacion_modelos.png")

# ── 5. Grafica 2 — Evolucion de precision ────────────────────
df_s = df.sort_values("sesion_id").copy()
df_s["prec_movil"] = df_s["fue_correcto"].rolling(30, min_periods=5).mean() * 100
fig, ax = plt.subplots(figsize=(10, 4.5))
fig.patch.set_facecolor("#040608"); ax.set_facecolor("#080c10")
ax.fill_between(df_s["sesion_id"], df_s["prec_movil"], alpha=0.15, color="#00d4ff")
ax.plot(df_s["sesion_id"], df_s["prec_movil"], color="#00d4ff", linewidth=2,
        label="Precision (ventana 30 diag.)")
ax.axhline(prec_actual, color="#ffd700", linewidth=1.2, linestyle="--",
           label=f"Media global {prec_actual:.1f}%")
ax.set_xlabel("Numero de diagnostico", color="#8aacbe")
ax.set_ylabel("Precision (%)", color="#8aacbe")
ax.set_title("Evolucion de la Precision — El Sistema Aprende con el Uso",
             color="#e8f0f8", fontsize=13, fontweight="bold")
ax.tick_params(colors="#8aacbe"); ax.spines[:].set_color("#1e2a36")
ax.grid(color="#141c24", linewidth=0.7)
ax.legend(facecolor="#0d1319", edgecolor="#1e2a36", labelcolor="#8aacbe")
plt.tight_layout()
plt.savefig(os.path.join(OUT, "evolucion_precision.png"),
            dpi=150, bbox_inches="tight", facecolor="#040608")
plt.close()
print("Grafica 2: evolucion_precision.png")

# ── 6. Grafica 3 — Fallas frecuentes ─────────────────────────
fc = df["falla_correcta_id"].value_counts().head(10)
nombres_f = [FALLA_NOMBRES.get(i, f"F{i}") for i in fc.index]
fig, ax = plt.subplots(figsize=(9, 5))
fig.patch.set_facecolor("#040608"); ax.set_facecolor("#080c10")
colores_f = ["#00d4ff" if i < 3 else "#1e5a70" for i in range(len(fc))]
ax.barh(nombres_f[::-1], fc.values[::-1], color=colores_f[::-1], height=0.6)
ax.set_xlabel("Cantidad de diagnosticos", color="#8aacbe")
ax.set_title("Top 10 Fallas Mas Diagnosticadas",
             color="#e8f0f8", fontsize=13, fontweight="bold")
ax.tick_params(colors="#8aacbe"); ax.spines[:].set_color("#1e2a36")
ax.grid(axis="x", color="#141c24", linewidth=0.7)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "fallas_frecuentes.png"),
            dpi=150, bbox_inches="tight", facecolor="#040608")
plt.close()
print("Grafica 3: fallas_frecuentes.png")

# ── 7. Grafica 4 — Matriz de confusion ───────────────────────
y_pred_best = mejor["pred"]
fallas_pres = sorted(set(y_test) | set(y_pred_best))
cm = confusion_matrix(y_test, y_pred_best, labels=fallas_pres)
etiquetas = [FALLA_NOMBRES.get(f, f"F{f}") for f in fallas_pres]
fig, ax = plt.subplots(figsize=(11, 9))
fig.patch.set_facecolor("#040608"); ax.set_facecolor("#080c10")
sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
            xticklabels=etiquetas, yticklabels=etiquetas,
            ax=ax, linewidths=0.3, linecolor="#141c24",
            cbar_kws={"shrink": 0.7})
ax.set_title(f"Matriz de Confusion — {mejor_nombre}",
             color="#e8f0f8", fontsize=12, fontweight="bold")
ax.set_xlabel("Predicho", color="#8aacbe")
ax.set_ylabel("Real", color="#8aacbe")
ax.tick_params(colors="#8aacbe", labelsize=8)
plt.xticks(rotation=40, ha="right"); plt.yticks(rotation=0)
plt.tight_layout()
plt.savefig(os.path.join(OUT, "matriz_confusion.png"),
            dpi=150, bbox_inches="tight", facecolor="#040608")
plt.close()
print("Grafica 4: matriz_confusion.png")

# ── 8. Reporte de texto ───────────────────────────────────────
rep_path = os.path.join(OUT, "reporte_modelos.txt")
with open(rep_path, "w", encoding="utf-8") as f:
    f.write("=" * 55 + "\n")
    f.write("  FrostAnalitic — Reporte de Ciencia de Datos\n")
    f.write("=" * 55 + "\n\n")
    f.write(f"Dataset: {len(df)} diagnosticos simulados\n")
    f.write(f"Equipos: {df['equipo'].nunique()} tipos\n")
    f.write(f"Fallas distintas: {df['falla_correcta_id'].nunique()}\n\n")
    f.write(f"Precision arbol de reglas actual: {prec_actual:.1f}%\n\n")
    f.write("Resultados por modelo:\n")
    for nombre, r in resultados.items():
        f.write(f"\n  {nombre}:\n")
        f.write(f"    Accuracy:            {r['acc']:.1f}%\n")
        f.write(f"    F1-Score (weighted): {r['f1']:.1f}%\n")
        f.write(f"    Cross-Val (5-fold):  {r['cv']:.1f}%\n")
    f.write(f"\nMejor modelo: {mejor_nombre}\n")
    f.write(f"Mejora sobre arbol de reglas: +{mejora:.1f}%\n\n")
    labels_rep   = sorted(set(y_test))
    target_names = [FALLA_NOMBRES.get(l, f"Falla {l}") for l in labels_rep]
    f.write(classification_report(y_test, y_pred_best,
            labels=labels_rep, target_names=target_names, zero_division=0))
print("Reporte: reporte_modelos.txt")

print("\n" + "=" * 55)
print("  RESUMEN PARA TU TESIS:")
print(f"  Arbol de reglas:  {prec_actual:.1f}%")
for n, r in resultados.items():
    print(f"  {n:<24} {r['acc']:.1f}%")
print(f"  Mejora obtenida:  +{mejora:.1f}%")
print(f"\n  Graficas en: {OUT}")
print("=" * 55)
