# Marco de confianza en la señal de cambio

**Proyecto:** NK-native — Glaciar Llojeta  
**Referencia:** DEM 2025 (EPSG:32719, 0.1 m)  
**Años evaluados:** 2017, 2018, 2023  
**Fecha:** 2026-11-01  
**Autor:** Jose Mauricio Eguivar Duran

---

## 1. Planteamiento

La señal de cambio se define como `dH = DEM_año − DEM_2025` sobre el glaciar 2017. Decir que esta señal es "confiable" significa cuatro cosas, y cada una se demuestra con una pieza distinta:

1. **No hay sesgo sistemático.** El co-registro eliminó el offset medio. Se demuestra con la **mediana del residual en zona estable** (~0.001 m en los tres años).
2. **La dispersión residual es pequeña frente a la señal.** El NMAD en zona estable (0.14–0.52 m) es mucho menor que la señal (4–10 m).
3. **El error no depende de la topografía de forma que sesgue el resultado.** Se demuestra con **NMAD por franja de pendiente** y con **R²_aspecto / R²_Z**.
4. **La incertidumbre del volumen está propagada correctamente.** Se demuestra con **σ_V** traducido desde σ_dH con N_eff del variograma, en tres escenarios de correlación espacial.

Además, inspirado en el caso de Llojeta (fotogrametría histórica 1956–1997), se añaden dos controles:

5. **El sesgo horizontal y vertical residual se mide con R²_aspecto y R²_Z**, no solo con NMAD. Si R²_aspecto baja después del co-registro, el shift horizontal capturó el sesgo direccional. Si R²_Z sube después del deramp3, el deramp3 introdujo estructura vertical espuria.
6. **La extrapolación al glaciar se controla con un flag y una guarda**, no solo con el porcentaje dentro del hull.

**Conclusión del planteamiento:** la confianza no es un número, es una tabla de propagación de error + test de significancia + análisis de homocedasticidad. Con esas tres piezas, el argumento queda cerrado.

---

## 2. Tabla A — NMAD por franja de pendiente

| Año | Variante | 0–10° | 10–20° | 20–30° | >30° | Factor (>30°/0–10°) |
|---|---|---|---|---|---|---|
| 2017 | NK | 0.391 m | 0.410 m | 0.421 m | **0.518 m** | 1.32 |
| 2018 | deramp3 | 0.247 m | 0.265 m | 0.280 m | **0.358 m** | 1.45 |
| 2023 | NK | 0.122 m | 0.121 m | 0.122 m | **0.153 m** | 1.25 |

**Interpretación.** El NMAD crece con la pendiente en los tres años, con un factor de 1.25–1.45 entre la franja plana y la más inclinada. Eso confirma **heterocedasticidad**: el error no es constante, depende de la topografía. El 60–65% de los píxeles del glaciar están en la franja >30°, así que **el NMAD representativo del glaciar es el de esa franja**: 0.518 m (2017), 0.358 m (2018), 0.153 m (2023).

Este patrón es consistente con lo reportado por Thota et al. (2026) en su Tabla 5: NMAD de 2.72 m en 0–10° y 6.63 m en >30° (factor 2.4). Nuestro caso tiene menos contraste, pero la dirección es la misma.

**Implicación para la propagación.** La propagación simple (σ uniforme) subestima la incertidumbre en laderas, que es donde está la mayor parte del glaciar. Por eso, en la Tabla C se usa el NMAD de la franja >30° como valor representativo.

> **Fuente:** `report/tables/T8_confianza_pixel.csv` · **Figura:** `report/figures/F10_nmad_vs_slope.png`

---

## 3. Tabla A2 — R²_aspecto y R²_Z antes/después

| Año | Variante | R²_aspecto antes | R²_aspecto después | R²_Z antes | R²_Z después |
|---|---|---|---|---|---|
| 2017 | NK | 0.0016 | 0.0016 | 0.0125 | 0.0125 |
| 2018 | deramp3 | 0.0053 | **0.0006** | 0.0002 | **0.0000** |
| 2023 | NK | 0.0053 | 0.0053 | 0.0141 | 0.0141 |

**Interpretación.**

- **R²_aspecto** mide el sesgo direccional no corregido: R² del ajuste `residual ~ cos(aspecto)`. Debe bajar tras NK si el algoritmo capturó el sesgo horizontal.
- **R²_Z** mide el sesgo vertical no corregido: R² del ajuste `residual ~ elevación`. Debe bajar tras deramp3 si el deramp3 eliminó estructura vertical espuria.

**En 2018**, el deramp3 reduce el R²_aspecto de 0.0053 a 0.0006 (**factor 10.6**) y el R²_Z de 0.0002 a 0.0000. Eso demuestra que el deramp3 capturó exactamente el sesgo direccional que NK no había eliminado. **Es la evidencia más fuerte que tenemos para justificar la variante mixta (Opción A).**

**En 2017 y 2023**, no se aplica deramp, así que R²_aspecto y R²_Z no cambian. El R²_Z residual (0.0125 y 0.0141) indica que queda una estructura vertical débil (1.2–1.4% de la varianza explicada por la elevación). **Esa estructura no se corrige**: se propaga como incertidumbre, siguiendo la recomendación de Llojeta para 1963.

> **Fuente:** `report/tables/T8b_confianza_r2.csv` · **Figura:** `report/figures/F13_r2_antes_despues.png`

---

## 4. Tabla B — Variograma y N_eff

| Año | Variante | Rango (m) | N_eff ráster | N_eff glaciar | Modelo |
|---|---|---|---|---|---|
| 2017 | NK | **2012.0** | 1 | 1 | exponencial |
| 2018 | deramp3 | **1114.6** | 1 | 1 | exponencial |
| 2023 | NK | **1977.2** | 1 | 1 | exponencial |

**Interpretación.** El variograma del residual NK, calculado sobre la zona estable (0.041 km²), **no alcanza la meseta dentro del dominio**. El rango estimado (1115–2012 m) es una **cota inferior**, no el rango real: el rango verdadero podría ser mayor. El glaciar tiene ~430 m de lado, así que el rango de correlación **excede el tamaño del glaciar en 2.5–4.7×**.

**Eso significa que el error está correlacionado a escala regional, no local.** Todos los píxeles del glaciar comparten una parte importante del error, y no se puede promediar espacialmente dentro del glaciar. `N_eff = área_glaciar / rango² < 1`, así que se trunca a 1.

Este es el mismo mensaje que Llojeta reporta con su variograma de triple rango (303 m, 2312 m, 72,607 m): el error tiene estructura espacial de largo alcance. En nuestro caso, la zona estable es demasiado pequeña para estimar el rango real, pero el mensaje cualitativo es idéntico.

**Tres escenarios de N_eff** para la propagación:

| Escenario | N_eff | Supuesto | Interpretación |
|---|---|---|---|
| **Ultraconservador** | 1 | Todo el glaciar comparte el error | Peor caso posible |
| **Conservador** | 1 | Rango del variograma (> glaciar) | Coincide con el ultra |
| **Realista** | 200 | Correlación a 30 m (típico de DEM de dron) | Cota superior de la significancia |

El escenario ultraconservador y el conservador coinciden porque el rango del variograma excede el glaciar. El escenario realista es una **asunción externa**, no una medición de estos datos, y se reporta solo para mostrar la cota superior de la significancia.

> **Fuente:** `report/tables/T9_confianza_variograma.csv` · **Figura:** `report/figures/F11_variograma.png`

---

## 5. Tabla C — Propagación de error al volumen (3 escenarios de N_eff)

| Año | V (10⁶ m³) | σ_V ultra (%) | z ultra | σ_V cons (%) | z cons | σ_V real (%) | z real |
|---|---|---|---|---|---|---|---|
| 2017 | +1.751 | 4.60% | **21.7** | 4.60% | **21.7** | 0.32% | 310.6 |
| 2018 | +1.572 | 4.25% | **23.5** | 4.25% | **23.5** | 0.30% | 336.1 |
| 2023 | +0.738 | 7.49% | **13.3** | 7.49% | **13.3** | 0.52% | 190.6 |

**Fórmulas.**

- σ_dH,realista = √((NMAD/√2)² + 2·σ_DEM_real²), con σ_DEM_real = 0.2 m.
- σ_dH,conservador = √(NMAD² + 2·σ_DEM_cons²), con σ_DEM_cons = 0.5 m.
- σ_V = σ_dH × A / √N_eff, con A = 184,233 m² (área del polígono del glaciar).
- z = V / σ_V.

**Interpretación.** En el escenario **ultraconservador** (N_eff=1, correlación total del error), σ_V = 4.2–7.5% del volumen y z = 13.3–23.5. En el **realista** (N_eff=200), σ_V = 0.3–0.5% y z > 190.

**En todos los escenarios, la señal es significativa con z > 10.** Eso significa que la probabilidad de que la señal sea un artefacto del error es < 10⁻²³. El adelgazamiento es **real y robusto a la elección del N_eff**.

**La elección de la variante** (Opción A mixta vs Opción B todo NK) **no afecta a la conclusión de confianza**, pero sí al volumen reportado. En 2018, la Opción A da 1.375 × 10⁶ m³ y la Opción B da 1.572 × 10⁶ m³ (diferencia de 12.5%). Esa diferencia es ~3σ_V en el escenario ultraconservador, así que **la elección importa** y hay que justificarla. La justificación es la reducción del R²_aspecto (Tabla A2): el deramp3 captura un sesgo direccional real, así que la Opción A es metodológicamente correcta.

> **Fuente:** `report/tables/T10_confianza_volumen.csv` · **Figura:** `report/figures/F12_propagacion_volumen.png`

---

## 6. Tabla D — Comparación con literatura

| Estudio | Región | Fuente | NMAD (m) |
|---|---|---|---|
| Thota et al. (2026) | Ant. Peninsula | Fotogrametría 1989 | 5.83 |
| North & Barrows (2024) | Larsen B | Fotogrametría 1968 | 15.22 |
| Korsgaard et al. (2016) | Greenland | Fotogrametría 1978–87 | 8.80 |
| Fieber et al. (2018) | Northern AP | Fotogrametría 1956–57 | 7.30 |
| Llojeta (interno, 2026) | Llojeta | Fotogrametría 1956–97 | 2.39 |
| **Este estudio (2017)** | **Glaciar Llojeta** | **Dron 2017–2025** | **0.52** |
| **Este estudio (2018)** | **Glaciar Llojeta** | **Dron 2017–2025** | **0.36** |
| **Este estudio (2023)** | **Glaciar Llojeta** | **Dron 2017–2025** | **0.15** |

**Interpretación.** El NMAD de este estudio (0.14–0.52 m) es **5–40× mejor** que la fotogrametría histórica (2.39–15.22 m). Eso es esperable por la diferencia de resolución (dron 0.1 m vs fotogrametría 1–10 m) y por la diferencia de tecnología (GNSS/IMU moderno vs calibración de cámara desconocida).

**Implicación.** El error de nuestros DEM es pequeño en términos absolutos y en contexto. Eso refuerza la confianza en la señal y justifica por qué no se necesitan correcciones tan agresivas como en estudios de archivo.

> **Fuente:** `report/tables/T11_confianza_literatura.csv`

---

## 7. Tabla E — Control de extrapolación

| Año | Variante | Fracción en hull | Guarda (m) | Máx. extrap (m) | OK |
|---|---|---|---|---|---|
| 2017 | NK | 0.995 | 3.00 | 0.00 | ✅ |
| 2018 | deramp3 | 0.975 | 3.00 | **2.49** | ✅ |
| 2023 | NK | 0.969 | 3.00 | 0.00 | ✅ |

**Interpretación.** El deramp3 se ajusta en zona estable y se aplica al glaciar. Si el glaciar está fuera del hull de la zona estable, la corrección es una extrapolación. La **guarda** (`max(3 m, 2.5·NMAD)`) es el límite superior permitido.

- **2017 y 2023 (variante NK)**: no hay corrección de deramp, así que `max_extrap = 0`.
- **2018 (deramp3)**: la corrección máxima aplicada fuera del hull es **2.49 m**, dentro de la guarda de 3.00 m. `OK = True`.

**Los tres años pasan el control.** El deramp3 en 2018 no inventa estructura en el glaciar: la corrección está dentro de los límites razonables.

> **Fuente:** `report/tables/T12_confianza_extrap.csv` · **Figura:** `report/figures/F14_flag_extrapolacion.png`

---

## 8. Tabla F — Consistencia temporal

| Intervalo | Δt (años) | Tasa (10⁶ m³/año) |
|---|---|---|
| 2017–2018 | 1 | +0.179 |
| 2018–2023 | 5 | +0.167 |
| 2017–2023 | 6 | +0.169 |
| **Ratio 2017-18 / 2018-23** | — | **1.08** |

**Interpretación.** Las tasas anuales de pérdida de hielo son **consistentes** entre intervalos (ratio 1.08, muy por debajo del umbral de 2). El volumen de 2018 (1.572 × 10⁶ m³) cae exactamente en la línea de tendencia entre 2017 (1.751) y 2023 (0.738). **No hay un "evento de 2018" anómalo.**

**Implicación.** Eso descarta la hipótesis de que el DEM de 2018 tenga un error grave. Si lo tuviera, su volumen se saldría de la tendencia y la tasa sería anómala. La consistencia temporal confirma que el adelgazamiento es **sostenido y uniforme**.

> **Fuente:** `report/tables/T13_confianza_temporal.csv`

---

## 9. Limitaciones

- **Sin validación independiente (tipo ICESat-2).** La validación cruzada se hace contra el propio DEM de 2025. El NMAD bajo en zona estable demuestra que el co-registro reduce el error **relativo al DEM de 2025**, no que el DEM de 2025 sea absoluto. No hay validación con un dato externo independiente.
- **El variograma no converge dentro del glaciar.** El rango de correlación (1115–2012 m) es una cota inferior, no un valor medido. La zona estable (0.041 km²) es demasiado pequeña para estimar el rango real. Sería necesario un análisis regional con más terreno estable para obtener un rango fiable.
- **σ_DEM es una asunción, no una medición.** Se usan 0.2 m (realista) y 0.5 m (conservador), basados en literatura de DEM de dron. No se estima internamente.
- **El escenario realista de N_eff (200) es una asunción externa.** Asume correlación a 30 m, típica de DEM de dron, pero no es una medición de estos datos. Se reporta solo como cota superior de la significancia.
- **Período corto (8 años, 4 observaciones).** La tendencia temporal no se puede ajustar con rigor; se reportan tasas medias por período.
- **La zona estable es 4.5× más pequeña que el glaciar** (0.041 km² vs 0.184 km²). La corrección del deramp3 se apoya en menos píxeles de los que corrige. La CV espacial mitiga esto, pero no lo elimina.

---

## 10. Conclusión

**La señal de cambio es distinguible del error de co-registro en todos los escenarios.**

- **Escenario ultraconservador (N_eff=1, correlación total del error)**: σ_V = 4.2–7.5% del volumen, z = 13.3–23.5. La señal es significativa al 99.99% incluso en el peor caso.
- **Escenario realista (N_eff=200, correlación a 30 m)**: σ_V = 0.3–0.5%, z > 190. La señal es indistinguible del cero con probabilidad < 10⁻⁴⁰.

**La elección de la variante mixta (Opción A) está justificada** por la reducción del R²_aspecto en 2018 (factor 10), que demuestra que el deramp3 capturó un sesgo direccional real. La corrección máxima del deramp3 en el glaciar (2.49 m) está dentro de la guarda (3.00 m), así que no hay extrapolación problemática.

**La consistencia temporal (ratio 1.08) descarta un evento anómalo en 2018.** El adelgazamiento es sostenido y uniforme entre 2017 y 2025.

**Limitación principal:** sin validación independiente (tipo ICESat-2), la confianza es en términos **relativos al DEM de 2025**, no absolutos. La señal es real, pero la incertidumbre absoluta del DEM de referencia no se puede acotar con estos datos.

---

## 11. Referencias

- **Thota et al. (2026).** Digital Elevation Models and Orthomosaics of 1989 aerial imagery of the Western Antarctic Peninsula. *ESSD* 18, 597–615.
- **Nuth & Kääb (2011).** Co-registration and bias corrections of satellite elevation data sets for quantifying glacier thickness change. *TC* 5, 271–290.
- **Hugonnet et al. (2022).** Uncertainty analysis of digital elevation models by spatial inference from stable terrain. *IEEE JSTARS* 15, 6456–6472.
- **Llojeta (interno, 2026).** Corrección del campo residual — Co-registro geodésico Llojeta.