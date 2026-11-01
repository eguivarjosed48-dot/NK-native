"""
Paso 5: genera un PDF de pre-informe con todos los insumos existentes
para revisión manual antes de redactar el informe científico final.

Incluye:
  - Portada
  - Tablas T3, T4, T5 (co-registro y DoD)
  - Tabla 10 (confianza: propagación al volumen, 3 escenarios)
  - Figuras F1–F9 + F10–F14
  - Pendientes para el informe final

NO sustituye al informe final. Es un dossier de revisión.
"""

import os
import csv
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle,
)
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

# ==============================================================================
# CONFIGURACIÓN
# ==============================================================================

REPORT_DIR = "report"
TABLES_DIR = os.path.join(REPORT_DIR, "tables")
FIGURES_DIR = os.path.join(REPORT_DIR, "figures")
OUTPUT_PDF = os.path.join(REPORT_DIR, "preinforme.pdf")

REFERENCE_YEAR = "2025"
YEARS = ["2017", "2018", "2023"]

FIGURAS = [
    ("F1_polygons_overview.png", "Figura 1. Vista general de polígonos",
     "Zona de terreno estable (verde) y glaciar 2017 (rojo) sobre el ráster de referencia."),
    ("F2_residuals_nk_hist.png", "Figura 2. Histogramas de residual NK",
     "Distribución del residual (DEM_año − DEM_2025) en zona estable tras el co-registro NK."),
    ("F3_residuals_nk_map.png", "Figura 3. Mapas de residual NK",
     "Estructura espacial del residual en zona estable. Permite ver si queda deformación no capturada."),
    ("F4_deramp_correction_map_2018.png", "Figura 4. Campo de corrección deramp3 en 2018",
     "Diferencia entre el DEM con deramp3 y el DEM con NK. Rojo = resta, azul = suma."),
    ("F5_deramp_vs_slope_aspect.png", "Figura 5. Corrección deramp3 vs pendiente y orientación (2018)",
     "Verifica si la corrección tiene sesgo direccional. Con polígono balanceado, debería ser plana."),
    ("F6_dod_maps.png", "Figura 6. Mapas del DoD",
     "Diferencia de elevación (DEM_año − DEM_2025) sobre el glaciar 2017. Valores positivos = pérdida."),
    ("F7_dod_histograms.png", "Figura 7. Histogramas del DoD",
     "Distribuciones del cambio de elevación por año. Permite comparar magnitud y dispersión."),
    ("F8_dod_hypsometry.png", "Figura 8. Hipsometría del cambio",
     "dH mediano por franja altitudinal. Muestra si el adelgazamiento es altitudinalmente dependiente."),
    ("F9_sensitivity_B_vs_A.png", "Figura 9. Sensibilidad Opción B vs Opción A",
     "Comparación de volúmenes entre la variante conservadora (todo NK) y la mixta (deramp3 en 2018)."),
    ("F10_nmad_vs_slope.png", "Figura 10. NMAD por franja de pendiente",
     "Heterocedasticidad del error: el NMAD crece con la pendiente en los tres años."),
    ("F11_variograma.png", "Figura 11. Rango de correlación del residual",
     "El rango (1115–2012 m) excede el tamaño del glaciar, indicando correlación de largo alcance."),
    ("F12_propagacion_volumen.png", "Figura 12. Propagación de error al volumen",
     "Tres escenarios de N_eff: ultraconservador (z>13), conservador (igual), realista (z>190)."),
    ("F13_r2_antes_despues.png", "Figura 13. R²_aspecto y R²_Z antes/después",
     "En 2018, el deramp3 reduce el R²_aspecto de 0.0053 a 0.0006 (factor 9)."),
    ("F14_flag_extrapolacion.png", "Figura 14. Cobertura del glaciar por el hull",
     "El 97–99% del glaciar está dentro del hull de la zona estable."),
]


# ==============================================================================
# UTILIDADES
# ==============================================================================

def leer_csv(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta) as f:
        return list(csv.DictReader(f))


def tabla_desde_csv(filas, columnas, titulo, col_widths=None):
    if not filas:
        return [Paragraph(f"<i>{titulo}: sin datos</i>", getSampleStyleSheet()["Normal"])]

    data = [[col[1] for col in columnas]]
    for fila in filas:
        row = []
        for key, _ in columnas:
            v = fila.get(key, "")
            try:
                f = float(v)
                if abs(f) < 1e-3 and f != 0:
                    row.append(f"{f:.3e}")
                elif abs(f) >= 1000:
                    row.append(f"{f:,.1f}")
                else:
                    row.append(f"{f:.3f}")
            except (ValueError, TypeError):
                row.append(str(v))
        data.append(row)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
    ]))
    return table


# ==============================================================================
# CONSTRUCCIÓN DEL PDF
# ==============================================================================

def main():
    print("=" * 70)
    print("PASO 5: PRE-INFORME PDF (dossier de revisión)")
    print("=" * 70)

    os.makedirs(REPORT_DIR, exist_ok=True)

    doc = SimpleDocTemplate(
        OUTPUT_PDF,
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="NK-native — Pre-informe de revisión",
        author="Jose Mauricio Eguivar Duran",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="TituloPortada", parent=styles["Title"],
        fontSize=24, alignment=TA_CENTER, spaceAfter=20,
    ))
    styles.add(ParagraphStyle(
        name="SubtituloPortada", parent=styles["Normal"],
        fontSize=12, alignment=TA_CENTER, textColor=colors.grey,
    ))
    styles.add(ParagraphStyle(
        name="H1", parent=styles["Heading1"],
        fontSize=16, spaceBefore=18, spaceAfter=10, textColor=colors.HexColor("#2C3E50"),
    ))
    styles.add(ParagraphStyle(
        name="H2", parent=styles["Heading2"],
        fontSize=13, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#34495E"),
    ))
    styles.add(ParagraphStyle(
        name="Cuerpo", parent=styles["Normal"],
        fontSize=10, alignment=TA_JUSTIFY, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Pie", parent=styles["Normal"],
        fontSize=8, alignment=TA_CENTER, textColor=colors.grey,
    ))

    story = []

    # --- Portada ---
    story.append(Spacer(1, 4 * cm))
    story.append(Paragraph("NK-native", styles["TituloPortada"]))
    story.append(Paragraph("Pre-informe de revisión de insumos", styles["SubtituloPortada"]))
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        f"Co-registro Nuth & Kääb + deramp + DoD de DEMs glaciares<br/>"
        f"Referencia: {REFERENCE_YEAR} | Años: {', '.join(YEARS)}",
        styles["SubtituloPortada"],
    ))
    story.append(Spacer(1, 6 * cm))
    story.append(Paragraph(
        f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/>"
        f"Ubicación: {os.path.abspath('.')}",
        styles["Pie"],
    ))
    story.append(PageBreak())

    # --- Sección 0: propósito ---
    story.append(Paragraph("0. Propósito de este documento", styles["H1"]))
    story.append(Paragraph(
        "Este PDF <b>no es el informe científico final</b>. Es un dossier de revisión "
        "que reúne todos los insumos ya generados por el pipeline 00→06: tablas de "
        "co-registro, tablas del DoD, tablas de confianza, diagnóstico glaciar–zona "
        "estable y las 14 figuras. Su objetivo es permitir una revisión visual y "
        "numérica rápida antes de redactar el informe definitivo.",
        styles["Cuerpo"],
    ))
    story.append(Paragraph(
        "Los pendientes para el informe final se listan en la sección 5.",
        styles["Cuerpo"],
    ))
    story.append(PageBreak())

    # --- Sección 1: resultados del co-registro ---
    story.append(Paragraph("1. Co-registro (Paso 2): variantes NK / deramp3 / deramp-CV", styles["H1"]))
    story.append(Paragraph(
        "Métricas del ajuste en zona estable. <b>NMAD</b>: dispersión robusta del residual. "
        "<b>CV</b>: validación cruzada espacial (leave-one-block-out). "
        "<b>CV acepta</b>: indica si el deramp3 mejora el NMAD fuera de muestra.",
        styles["Cuerpo"],
    ))
    filas_t3 = leer_csv(os.path.join(TABLES_DIR, "T3_coreg_step2_variants.csv"))
    story.append(tabla_desde_csv(
        filas_t3,
        [("year", "Año"), ("n_valid", "N válidos"),
         ("nmad_nk", "NMAD NK (m)"), ("nmad_deramp3", "NMAD d3 (m)"),
         ("nmad_cv", "NMAD CV (m)"), ("nmad_nk_cv", "NMAD NKcv (m)"),
         ("cv_acepta", "CV acepta"), ("nmad_derampCV", "NMAD final (m)")],
        "Tabla T3",
    ))
    story.append(Spacer(1, 1 * cm))

    # --- Sección 2: resultados del DoD ---
    story.append(Paragraph("2. DoD (Paso 3): volúmenes de cambio", styles["H1"]))
    story.append(Paragraph(
        "Convención de signo: <b>dH = DEM_año − DEM_2025</b>. "
        "Valores positivos indican que el glaciar era más grueso en el año comparado "
        "que en 2025, es decir, <b>pérdida de masa</b> entre ambos años.",
        styles["Cuerpo"],
    ))
    filas_t4 = leer_csv(os.path.join(TABLES_DIR, "T4_dod_summary.csv"))
    story.append(tabla_desde_csv(
        filas_t4,
        [("year", "Año"), ("option", "Opción"), ("variant", "Variante"),
         ("n_pixels", "N píxeles"), ("dh_mean_m", "dH medio (m)"),
         ("dh_median_m", "dH mediana (m)"), ("dh_nmad_m", "NMAD (m)"),
         ("volume_m3", "Volumen (m³)")],
        "Tabla T4",
    ))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "<b>Opción B</b>: todos los años con NK (consistencia metodológica). "
        "<b>Opción A</b>: variante mixta (2017 y 2023 con NK, 2018 con deramp3, "
        "según decisión de la CV). La diferencia entre ambas es la sensibilidad "
        "metodológica del resultado.",
        styles["Cuerpo"],
    ))
    story.append(PageBreak())

    # --- Sección 3: diagnóstico glaciar vs estable ---
    story.append(Paragraph("3. Diagnóstico glaciar vs zona estable", styles["H1"]))
    story.append(Paragraph(
        "Evalúa si el glaciar está dentro del convex hull de la zona estable y a qué "
        "distancia. Determina si la extrapolación del polinomio deramp al glaciar es "
        "defendible.",
        styles["Cuerpo"],
    ))
    filas_t5 = leer_csv(os.path.join(TABLES_DIR, "T5_glacier_vs_stable.csv"))
    if filas_t5:
        fila = filas_t5[0]
        data_t5 = [["Métrica", "Valor"]]
        etiquetas = {
            "stable_pixels": "Píxeles zona estable",
            "glacier_pixels": "Píxeles glaciar",
            "stable_area_km2": "Área zona estable (km²)",
            "glacier_area_km2": "Área glaciar (km²)",
            "hull_area_km2": "Área hull (km²)",
            "glacier_frac_inside_hull": "Fracción glaciar dentro del hull",
            "glacier_centroid_inside_hull": "Centroide dentro del hull",
            "dist_min_m": "Distancia mínima (m)",
            "dist_p5_m": "Distancia P5 (m)",
            "dist_p25_m": "Distancia P25 (m)",
            "dist_median_m": "Distancia mediana (m)",
            "dist_p75_m": "Distancia P75 (m)",
            "dist_p95_m": "Distancia P95 (m)",
            "dist_max_m": "Distancia máxima (m)",
        }
        for k, label in etiquetas.items():
            v = fila.get(k, "")
            try:
                f = float(v)
                if "frac" in k:
                    v_fmt = f"{f:.3f} ({100*f:.1f}%)"
                elif "pixels" in k:
                    v_fmt = f"{int(f):,}"
                elif abs(f) < 1:
                    v_fmt = f"{f:.6f}"
                else:
                    v_fmt = f"{f:.2f}"
            except (ValueError, TypeError):
                v_fmt = str(v)
            data_t5.append([label, v_fmt])

        t5_table = Table(data_t5, colWidths=[9 * cm, 5 * cm])
        t5_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ]))
        story.append(t5_table)
    story.append(PageBreak())

    # --- Sección 3b: confianza en la señal ---
    story.append(Paragraph("3b. Confianza en la señal de cambio (Paso 6)", styles["H1"]))
    story.append(Paragraph(
        "La propagación de error se evalúa en tres escenarios de correlación espacial: "
        "<b>ultraconservador</b> (N_eff=1, todo el glaciar comparte el error), "
        "<b>conservador</b> (N_eff del variograma, que coincide con el ultra porque el "
        "rango de correlación excede el glaciar) y <b>realista</b> (N_eff=200, asunción "
        "de correlación a 30 m, típica de DEM de dron). "
        "En todos los escenarios, la señal es significativa con z > 10.",
        styles["Cuerpo"],
    ))
    t10_rows = leer_csv(os.path.join(TABLES_DIR, "T10_confianza_volumen.csv"))
    if t10_rows:
        data_t10 = [["Año", "Variante", "V (10⁶ m³)", "σ_V ultra (%)", "z ultra",
                     "σ_V real (%)", "z real"]]
        for r in t10_rows:
            data_t10.append([
                r["year"],
                r["variant"],
                f"{float(r['volume_m3'])/1e6:+.3f}",
                f"{float(r['sv_real_ultra_pct']):.2f}",
                f"{float(r['z_real_ultra']):.1f}",
                f"{float(r['sv_real_real_pct']):.2f}",
                f"{float(r['z_real_real']):.1f}",
            ])
        t10_table = Table(data_t10,
                          colWidths=[1.5*cm, 2*cm, 2.5*cm, 2.5*cm, 2*cm, 2.5*cm, 2*cm])
        t10_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ]))
        story.append(t10_table)
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(
            "Los valores de z > 10 indican que la señal de cambio es distinguible del "
            "error de co-registro incluso en el peor caso posible (correlación total del "
            "error). En el escenario realista, z > 190, lo que confirma que la conclusión "
            "es robusta a la elección del N_eff.",
            styles["Cuerpo"],
        ))
    story.append(PageBreak())

    # --- Sección 3c: control de extrapolación ---
    story.append(Paragraph("3c. Control de extrapolación del deramp3", styles["H1"]))
    story.append(Paragraph(
        "El deramp3 se ajusta en zona estable y se aplica al glaciar. Si el glaciar está "
        "fuera del hull de la zona estable, la corrección es una extrapolación. La "
        "<b>guarda</b> (max(3 m, 2.5·NMAD)) es el límite superior permitido.",
        styles["Cuerpo"],
    ))
    t12_rows = leer_csv(os.path.join(TABLES_DIR, "T12_confianza_extrap.csv"))
    if t12_rows:
        data_t12 = [["Año", "Variante", "Frac. hull", "Guarda (m)", "Máx. extrap (m)", "OK"]]
        for r in t12_rows:
            data_t12.append([
                r["year"], r["variant"],
                f"{float(r['frac_in_hull']):.3f}",
                f"{float(r['guarda_m']):.2f}",
                f"{float(r['max_extrap_glaciar_m']):.2f}",
                r["extrap_ok"],
            ])
        t12_table = Table(data_t12, colWidths=[1.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm, 1.5*cm])
        t12_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2C3E50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ]))
        story.append(t12_table)
        story.append(Spacer(1, 0.5 * cm))
        story.append(Paragraph(
            "Los tres años pasan el control (OK=True). La corrección máxima del deramp3 en "
            "2018 (2.49 m) está dentro de la guarda (3.00 m). No hay extrapolación problemática.",
            styles["Cuerpo"],
        ))
    story.append(PageBreak())

    # --- Sección 4: figuras ---
    story.append(Paragraph("4. Figuras del análisis", styles["H1"]))
    story.append(Paragraph(
        "Las 14 figuras generadas por los Pasos 4 y 6, en orden de aparición previsto "
        "en el informe final. Cada una se presenta con su pie de figura.",
        styles["Cuerpo"],
    ))
    story.append(PageBreak())

    for fname, titulo, descripcion in FIGURAS:
        ruta = os.path.join(FIGURES_DIR, fname)
        story.append(Paragraph(titulo, styles["H2"]))
        if os.path.exists(ruta):
            from PIL import Image as PILImage
            with PILImage.open(ruta) as im:
                w, h = im.size
            max_w = 16 * cm
            max_h = 20 * cm
            ratio = min(max_w / w, max_h / h)
            img = Image(ruta, width=w * ratio, height=h * ratio)
            story.append(img)
        else:
            story.append(Paragraph(f"<i>Figura no encontrada: {ruta}</i>", styles["Cuerpo"]))
        story.append(Spacer(1, 0.3 * cm))
        story.append(Paragraph(descripcion, styles["Cuerpo"]))
        story.append(PageBreak())

    # --- Sección 5: pendientes para el informe final ---
    story.append(Paragraph("5. Pendientes para el informe final", styles["H1"]))
    pendientes = [
        "<b>Redactar el informe final</b>: convertir el <i>T6_report_main.md</i> en prosa "
        "científica con introducción, métodos, resultados, discusión y conclusiones.",
        "<b>Interpretación visual de F8</b>: describir el patrón altitudinal del "
        "adelgazamiento (mayor en la lengua o en la zona de acumulación).",
        "<b>Decisión final de convención de signo</b>: documentar dH = DEM_año − DEM_2025 "
        "y volumen positivo = pérdida de masa.",
        "<b>Contexto climático</b>: contrastar la tasa de adelgazamiento (1.2 m/año en "
        "2017–2025, 2.0 m/año en 2023–2025) con datos meteorológicos o estudios previos "
        "de la zona, si están disponibles.",
        "<b>Limitaciones a documentar</b>: sin validación independiente (tipo ICESat-2); "
        "variograma no converge dentro del glaciar; N_eff es una cota inferior; σ_DEM "
        "asumido (0.2–0.5 m).",
    ]
    for p in pendientes:
        story.append(Paragraph(f"• {p}", styles["Cuerpo"]))
        story.append(Spacer(1, 0.2 * cm))

    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph(
        "<i>Fin del pre-informe. Este documento es un dossier de revisión, no el "
        "informe científico final.</i>",
        styles["Pie"],
    ))

    # --- Construir PDF ---
    doc.build(story)
    print(f"\nPDF generado: {os.path.abspath(OUTPUT_PDF)}")
    print(f"Tamaño: {os.path.getsize(OUTPUT_PDF) / 1024 / 1024:.2f} MB")
    print("=" * 70)


if __name__ == "__main__":
    main()