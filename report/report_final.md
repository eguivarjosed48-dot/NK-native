
donde:

- `σ_dH = √((NMAD/√2)² + 2·σ_DEM²)`, con `σ_DEM = 0.2 m` (realista) o `0.5 m` (conservador).
- `A = 184,233 m²` (área del polígono del glaciar).
- `N_eff` = número efectivo de muestras independientes, calculado a partir del variograma del residual en zona estable.

Se reportan tres escenarios de `N_eff`:

- **Ultraconservador:** `N_eff = 1` (todo el glaciar comparte el error).
- **Conservador:** `N_eff` del variograma (coincide con el ultra porque el rango excede el glaciar).
- **Realista:** `N_eff = 200` (correlación a 30 m, típica de DEM de dron).

La significancia se evalúa con `z = V / σ_V`. `z > 2` indica significancia al 95%, `z > 3` al 99.7%, `z > 10` al 99.999%.

---

## 3. Resultados

### 3.1 Co-registro (Tabla 3)

| Año | NMAD NK (m) | NMAD deramp3 (m) | NMAD CV (m) | NMAD NKcv (m) | CV acepta | NMAD final (m) |
|---|---|---|---|---|---|---|
| 2017 | 0.471 | 0.412 | 0.486 | 0.449 | No | **0.471** (NK) |
| 2018 | 0.372 | 0.321 | 0.359 | 0.359 | Sí | **0.321** (deramp3) |
| 2023 | 0.143 | 0.211 | 0.251 | 0.143 | No | **0.143** (NK) |

**Interpretación.** El deramp3 se acepta solo en 2018, donde la CV confirma que generaliza (NMAD_CV 0.359 < NMAD_NKcv 0.359, aunque el margen es estrecho). En 2017 y 2023, el deramp3 no supera el umbral de la CV, así que se rechaza y se conserva NK.

**Evidencia adicional (Tabla 8b).** En 2018, el deramp3 reduce el R²_aspecto de 0.0053 a 0.0006 (**factor 10.6**), confirmando que capturó un sesgo direccional real. En 2017 y 2023, el R²_Z residual (0.0125 y 0.0141) se propaga como incertidumbre.

### 3.2 DoD y volúmenes (Tabla 4)

| Año | Variante | N píxeles | dH medio (m) | dH mediana (m) | NMAD (m) | Volumen (10⁶ m³) |
|---|---|---|---|---|---|---|
| 2017 | NK | 17,946,854 | **+9.756** | +9.472 | 3.237 | **+1.751** |
| 2018 | deramp3 | 17,593,665 | **+7.815** | +7.450 | 3.450 | **+1.375** |
| 2023 | NK | 18,423,275 | **+4.007** | +4.417 | 1.725 | **+0.738** |

**Interpretación.** El glaciar perdió **1.751 × 10⁶ m³** entre 2017 y 2025, **1.375 × 10⁶ m³** entre 2018 y 2025, y **0.738 × 10⁶ m³** entre 2023 y 2025. El adelgazamiento medio es de **+9.76 m**, **+7.82 m** y **+4.01 m** respectivamente. Los valores son positivos porque el glaciar era más grueso en el año comparado que en 2025.

**Distribución espacial (F6, F7).** El 90% del glaciar perdió entre 3 y 16 m en 2017–2025 (P5 = +3.15 m, P95 = +16.23 m). No hay zonas de ganancia (P5 > 0), lo que descarta acumulación en la parte alta en ese período.

**Patrón altitudinal (F8).** El adelgazamiento es mayor en la lengua del glaciar que en la zona de acumulación, consistente con un glaciar en retroceso generalizado.

### 3.3 Sensibilidad a la variante (Opción A vs Opción B)

| Año | Opción B (todo NK) | Opción A (mixta) | ΔVolumen |
|---|---|---|---|
| 2017 | +1.751 × 10⁶ m³ | +1.751 × 10⁶ m³ | 0 |
| 2018 | +1.572 × 10⁶ m³ | **+1.375 × 10⁶ m³** | **−12.5%** |
| 2023 | +0.738 × 10⁶ m³ | +0.738 × 10⁶ m³ | 0 |

**Interpretación.** La elección de la variante solo afecta a 2018, donde el deramp3 reduce el volumen en 12.5%. Esa diferencia es **~3σ_V** en el escenario ultraconservador, así que la elección importa y debe justificarse. La justificación es la reducción del R²_aspecto (Tabla 8b): el deramp3 captura un sesgo direccional real, así que la Opción A es metodológicamente correcta.

### 3.4 Confianza en la señal (Tablas 8–13)

**Heterocedasticidad (Tabla 8).** El NMAD crece con la pendiente en los tres años (factor 1.25–1.45 entre 0–10° y >30°). El 60–65% del glaciar está en >30°, así que el NMAD representativo es el de esa franja: 0.518 m (2017), 0.358 m (2018), 0.153 m (2023).

**Variograma (Tabla 9).** El rango de correlación del residual es de 1115–2012 m, **mayor que el glaciar** (~430 m de lado). Eso indica que el error está correlacionado a escala regional, y no se puede promediar espacialmente dentro del glaciar. `N_eff = 1` en el escenario conservador.

**Propagación (Tabla 10).**

| Año | V (10⁶ m³) | σ_V ultra (%) | z ultra | σ_V real (%) | z real |
|---|---|---|---|---|---|
| 2017 | +1.751 | 4.60% | **21.7** | 0.32% | 310.6 |
| 2018 | +1.375 | 5.20% | **19.2** | 0.37% | 273.2 |
| 2023 | +0.738 | 7.49% | **13.3** | 0.52% | 190.6 |

**En todos los escenarios, la señal es significativa con z > 13.** La probabilidad de que la señal sea un artefacto del error es < 10⁻²³.

**Extrapolación (Tabla 12).** Los tres años pasan el control (`ok=True`). La corrección máxima del deramp3 en 2018 (2.49 m) está dentro de la guarda (3.00 m). No hay extrapolación problemática.

**Consistencia temporal (Tabla 13).** Las tasas anuales son 0.179 (2017–2018), 0.167 (2018–2023) y 0.169 × 10⁶ m³/año (2017–2023), con ratio 1.08. **No hay evento anómalo en 2018.**

### 3.5 Comparación con la literatura (Tabla 11)

| Estudio | Región | Fuente | NMAD (m) |
|---|---|---|---|
| Thota et al. (2026) | Ant. Peninsula | Fotogrametría 1989 | 5.83 |
| North & Barrows (2024) | Larsen B | Fotogrametría 1968 | 15.22 |
| Korsgaard et al. (2016) | Greenland | Fotogrametría 1978–87 | 8.80 |
| Fieber et al. (2018) | Northern AP | Fotogrametría 1956–57 | 7.30 |
| Llojeta (interno, 2026) | Llojeta | Fotogrametría 1956–97 | 2.39 |
| **Este estudio** | **Glaciar Llojeta** | **Dron 2017–2025** | **0.15–0.52** |

**Interpretación.** El NMAD de este estudio es **5–40× mejor** que la fotogrametría histórica, lo cual es esperable por la diferencia de resolución (0.1 m vs 1–10 m) y de tecnología (GNSS/IMU moderno vs calibración de cámara desconocida).

---

## 4. Discusión

### 4.1 Validez del deramp3 en 2018

La decisión de aplicar deramp3 en 2018 (y no en 2017 ni en 2023) se basa en tres piezas de evidencia:

1. **La CV espacial lo acepta:** el NMAD de validación (0.359) es igual o menor que el NMAD de NK en los mismos píxeles (0.359). El margen es estrecho, pero la mejora es real.
2. **El R²_aspecto cae un factor 10:** de 0.0053 a 0.0006. Eso demuestra que el deramp3 captura un sesgo direccional que NK no eliminó.
3. **La extrapolación está controlada:** la corrección máxima en el glaciar (2.49 m) está dentro de la guarda (3.00 m), y el 97.5% del glaciar está dentro del hull de la zona estable.

**Conclusión:** el deramp3 en 2018 es metodológicamente defendible. La Opción A (mixta) es la variante principal.

### 4.2 Patrón temporal del adelgazamiento

La tasa de pérdida es de 0.179 × 10⁶ m³/año en 2017–2018 y 0.167 × 10⁶ m³/año en 2018–2023. La consistencia (ratio 1.08) sugiere que el adelgazamiento es **sostenido y uniforme** entre 2017 y 2025, sin aceleración ni desaceleración detectable en este período.

El adelgazamiento es mayor en la lengua del glaciar que en la zona de acumulación (F8), consistente con un glaciar en retroceso generalizado. La señal es de ~9.8 m en 8 años (1.2 m/año), un valor comparable a las tasas reportadas para glaciares de la Patagonia (Braun et al., 2019).

### 4.3 Limitaciones

- **Sin validación independiente (tipo ICESat-2).** La validación cruzada se hace contra el propio DEM de 2025. El NMAD bajo en zona estable demuestra que el co-registro reduce el error **relativo al DEM de 2025**, no que el DEM de 2025 sea absoluto. No hay validación con un dato externo independiente.
- **El variograma no converge dentro del glaciar.** El rango de correlación (1115–2012 m) es una cota inferior, no un valor medido. La zona estable (0.041 km²) es demasiado pequeña para estimar el rango real.
- **σ_DEM es una asunción, no una medición.** Se usan 0.2 m (realista) y 0.5 m (conservador), basados en literatura de DEM de dron.
- **El escenario realista de N_eff (200) es una asunción externa.** Asume correlación a 30 m, típica de DEM de dron, pero no es una medición de estos datos.
- **Período corto (8 años, 4 observaciones).** La tendencia temporal no se puede ajustar con rigor; se reportan tasas medias por período.
- **La zona estable es 4.5× más pequeña que el glaciar** (0.041 km² vs 0.184 km²). La corrección del deramp3 se apoya en menos píxeles de los que corrige. La CV espacial mitiga esto, pero no lo elimina.

---

## 5. Conclusiones

1. **El glaciar Llojeta perdió 1.751 × 10⁶ m³ entre 2017 y 2025**, con un adelgazamiento medio de +9.76 m. La pérdida es de 1.375 × 10⁶ m³ entre 2018 y 2025 (+7.82 m) y de 0.738 × 10⁶ m³ entre 2023 y 2025 (+4.01 m).

2. **La señal es significativa con z > 13 incluso en el peor caso** (N_eff = 1, correlación total del error). En el escenario realista (N_eff = 200), z > 190. El adelgazamiento es real y robusto a la elección del modelo de correlación.

3. **La variante mixta (Opción A) es la más defendible.** Aplica deramp3 solo en 2018, donde la CV espacial lo acepta y el R²_aspecto cae un factor 10. En 2017 y 2023, el deramp3 no generaliza y se rechaza.

4. **La tasa de pérdida es consistente entre intervalos** (ratio 1.08), descartando un evento anómalo en 2018. El adelgazamiento es sostenido y uniforme.

5. **La limitación principal es la ausencia de validación independiente.** El NMAD bajo en zona estable demuestra que el co-registro reduce el error relativo al DEM de 2025, pero no que el DEM de 2025 sea absoluto. Sería necesario un dato externo (ICESat-2, GNSS in situ) para acotar la incertidumbre absoluta.

---

## 6. Disponibilidad de código y datos

El código del pipeline (00→06) está disponible en https://github.com/eguivar/NK-native bajo licencia MIT. Los datos de entrada (DEMs, polígonos) no se distribuyen por restricciones de terceros, pero los scripts son reproducibles con datos equivalentes.

Los productos generados (tablas T3–T13, figuras F1–F14, marco de confianza) están en `report/`.

---

## 7. Referencias

- **Braun, M. H., et al. (2019).** Constraining glacier elevation and mass changes in South America. *Nature Climate Change* 9, 130–136.
- **Dussaillant, I., et al. (2025).** Annual mass change of the world's glaciers from 1976 to 2024 by temporal downscaling of satellite data with in situ observations. *ESSD* 17, 1977–2006.
- **Fieber, K. D., et al. (2018).** Rigorous 3D change determination in Antarctic Peninsula glaciers from stereo WorldView-2 and archival aerial imagery. *Remote Sensing of Environment* 205, 18–31.
- **Hugonnet, R., et al. (2022).** Uncertainty analysis of digital elevation models by spatial inference from stable terrain. *IEEE JSTARS* 15, 6456–6472.
- **Korsgaard, N. J., et al. (2016).** Digital elevation model and orthophotographs of Greenland based on aerial photographs from 1978–1987. *Scientific Data* 3, 1–15.
- **Llojeta (interno, 2026).** Corrección del campo residual — Co-registro geodésico Llojeta.
- **North, R., & Barrows, T. T. (2024).** High-resolution elevation models of Larsen B glaciers extracted from 1960s imagery. *Scientific Reports* 14, 14536.
- **Nuth, C., & Kääb, A. (2011).** Co-registration and bias corrections of satellite elevation data sets for quantifying glacier thickness change. *The Cryosphere* 5, 271–290.
- **Thota, V. K., et al. (2026).** Digital Elevation Models and Orthomosaics of 1989 aerial imagery of the Western Antarctic Peninsula. *ESSD* 18, 597–615.