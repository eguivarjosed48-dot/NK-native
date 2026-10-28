# Balance de masa geodésico del Glaciar Llojeta (Andes tropicales, 2017–2025) a partir de DSM de dron: co-registro Nuth & Kääb y validación cruzada espacial

**Jose Mauricio Eguivar Duran**<sup>1</sup>

<sup>1</sup> Autor independiente. Correo de contacto: eguivar.jose.d48@gmail.com

---

## Resumen

La diferencia de modelos digitales de superficie (DoD) es una de las pocas vías
para cuantificar el cambio de volumen de glaciares pequeños y sin series de
balance de masa *in situ*. Su precisión depende críticamente de dos pasos: el
co-registro de cada DSM a una referencia común y la corrección de sesgos
espacialmente sistemáticos (deramp), cuya extrapolación fuera del terreno de
control rara vez se evalúa. En este trabajo se estima el cambio de elevación del
Glaciar Llojeta (Cordillera Real, La Paz, Bolivia; ≈16,05° S, 68,30° O; 0,18 km²;
5.035–5.272 m s.n.m.) entre 2017, 2018 y 2023 respecto de un DSM de referencia de
2025,
utilizando cuatro DSM derivados de fotogrametría con dron sobre una cuadrícula
común de 0,1 m (EPSG:32719). El co-registro se resolvió con el algoritmo de
Nuth & Kääb, seguido de un deramp polinómico bidimensional de grado 3 y de una
validación cruzada espacial bloqueada (4 × 4) que decide, por año, si la
corrección polinómica mejora el ajuste fuera de muestra. La incertidumbre del
volumen se propagó desde el ruido del co-registro y su longitud de correlación
espacial, estimada con el variograma experimental del residual en terreno
estable. El cambio de elevación medio (dH = DEM<sub>año</sub> −
DEM<sub>2025</sub>) fue de +9,76 m (2017), +8,93 m (2018) y +4,01 m (2023)
—medianas de +9,47, +8,80 y +4,42 m—, equivalentes a tasas de adelgazamiento de
1,22, 1,28 y 2,00 m a⁻¹. Los volúmenes de cambio acumulados son +1,75 × 10⁶,
+1,57 × 10⁶ y +0,74 × 10⁶ m³ (pérdida de masa), con una incertidumbre aleatoria
inferior al 0,1 % y una incertidumbre total estimada del 10–15 %, dominada por
términos sistemáticos. La validación cruzada espacial rechazó el deramp en los
tres años pese a que éste mejoraba el ajuste *in-sample* hasta un 14 %;
aplicarlo sin esa verificación habría reducido los volúmenes entre un 5,2 % y un
12,5 % (hasta 0,20 × 10⁶ m³ en 2018), lo que cuantifica la sensibilidad del
resultado a una decisión metodológica que habitualmente se toma sin prueba
estadística. El adelgazamiento es máximo en el sector medio-bajo del glaciar
(≈5.040–5.100 m) y decrece hacia la cabecera, y los resultados son robustos a la
elección de variante para 2017 y 2023.

**Palabras clave:** balance de masa geodésico; DEM de diferencia; co-registro
Nuth & Kääb; deramp polinómico; validación cruzada espacial; variograma; glaciares
andinos; fotogrametría con dron.

## Abstract

DEM differencing (DoD) is one of the few available means to quantify volume
change of small glaciers lacking in-situ mass-balance series, and its accuracy
hinges on two steps: co-registration of every DEM to a common reference and the
correction of spatially systematic biases (deramp), whose extrapolation beyond
the control terrain is seldom assessed. We quantify elevation change of a
Llojeta Glacier, Cordillera Real, La Paz, Bolivia (≈16.05° S, 68.30° W; 0.18 km²;
5,035–5,272 m a.s.l.) between 2017, 2018 and 2023 relative to a 2025 reference
DSM, using four
drone-derived DSMs on a common 0.1 m grid (EPSG:32719). Co-registration used the
Nuth & Kääb algorithm, followed by a third-order two-dimensional polynomial
deramp and a blocked (4 × 4) spatial cross-validation that decides, year by
year, whether the polynomial correction improves the out-of-sample fit. Volume
uncertainty was propagated from the co-registration noise level and its spatial
correlation length, estimated with the experimental variogram of the
stable-terrain residuals. Mean elevation change (dH = DEM<sub>year</sub> −
DEM<sub>2025</sub>) was +9.76 m (2017), +8.93 m (2018) and +4.01 m (2023)
—medians of +9.47, +8.80 and +4.42 m—, i.e. thinning rates of 1.22, 1.28 and
2.00 m a⁻¹. Cumulative volume change is +1.75 × 10⁶, +1.57 × 10⁶ and
+0.74 × 10⁶ m³ (mass loss), with a random uncertainty below 0.1 % and a total
uncertainty estimated at 10–15 %, dominated by systematic terms. Blocked spatial
cross-validation rejected the deramp in all three years despite in-sample NMAD
improvements of up to 14 %; applying it without that test would have lowered
volumes by 5.2–12.5 % (up to 0.20 × 10⁶ m³ in 2018), quantifying the sensitivity
of the result to a methodological choice usually made without statistical
testing.
Thinning peaks in the mid-lower part of the glacier (≈5,040–5,100 m) and
decreases towards the headwall, and results are robust to the variant choice for
2017 and 2023.

**Keywords:** geodetic mass balance; DEM of difference; Nuth & Kääb
co-registration; polynomial deramp; spatial cross-validation; variogram; Andean
glaciers; drone photogrammetry.

---

## 1. Introducción

El balance de masa glaciar es un indicador directo del estado del sistema
climático y un insumo esencial para estimar la contribución de los glaciares al
nivel del mar (Zemp et al., 2019; Hugonnet et al., 2021). En los Andes
tropicales, una fracción importante de los glaciares carece de series
glaciológicas continuas, de modo que el balance geodésico —la conversión de un
cambio de volumen medido entre dos fechas en un cambio de masa— constituye la
única alternativa práctica para documentar su evolución (Paul et al., 2015).

El balance geodésico se obtiene típicamente restando dos modelos digitales de
elevación (DEM) y sumando la diferencia sobre un polígono de referencia
(*DEM of Difference*, DoD). La técnica es conceptualmente simple, pero la
diferencia entre dos DEM incluye, además del cambio real de la superficie,
errores de posicionamiento, de actitud y de modelo que se manifiestan como
desplazamientos horizontales y verticales y como deformaciones de baja
frecuencia (Nuth & Kääb, 2011). El procedimiento estándar combina por tanto dos
correcciones: (i) un co-registro que estima y elimina el desplazamiento
tridimensional residual entre cada DEM y uno de referencia, y (ii) un ajuste
polinómico suave —deramp— que absorbe las deformaciones de mayor longitud de
onda (Nuth & Kääb, 2011). Ambos se calibran sobre terreno estable, es decir,
sobre superficies que se supone no cambian entre las dos fechas.

El deramp introduce, no obstante, un compromiso difícil de verificar: al ser un
ajuste de tendencia global, su valor sobre el glaciar es en buena medida una
extrapolación desde las áreas estables, y nada garantiza *a priori* que una
corrección que mejora el ajuste en el terreno de control también lo haga sobre
la masa de hielo. En glaciares pequeños rodeados de afloramientos rocosos, el
terreno estable disponible suele ser escaso y geométricamente desfavorable, lo
que agrava el problema. La verificación empírica de esa decisión requiere una
evaluación fuera de muestra; sin embargo, en la práctica se suele adoptar el
deramp por convención, o descartarlo si el error en terreno estable empeora
*in-sample*, sin una prueba espacialmente honesta.

Este trabajo tiene tres objetivos. Primero, estimar el cambio de elevación y de
volumen del Glaciar Llojeta (~0,18 km²) entre 2017, 2018 y 2023 respecto de un
DSM de referencia de 2025, con datos de dron a 0,1 m de resolución. Segundo,
someter la decisión de aplicar el deramp a una validación cruzada espacial
bloqueada, de modo que la variante elegida se justifique con una métrica fuera
de muestra y no con una convención. Tercero, propagar la incertidumbre del
volumen a partir de la estructura de autocorrelación espacial de los residuales
—estimada con el variograma experimental— en lugar de suponer una fracción
arbitraria de píxeles independientes (Rolstad et al., 2009).

El conjunto de datos empleado es inusualmente favorable en resolución —0,1 m,
es decir, dos órdenes de magnitud más fino que los DEM satelitales habituales—
pero desfavorable en extensión, ya que el terreno estable disponible representa
apenas el 22 % del área del glaciar y se distribuye en franjas estrechas que
ro dean la masa de hielo. Esa combinación permite examinar, con datos reales,
hasta qué punto el deramp es defendible en un caso de control limitado, que es
precisamente el escenario típico de los glaciares pequeños de montaña.

---

## 2. Área de estudio

El área de estudio es el Glaciar Llojeta, un glaciar de montaña de la Cordillera
Real en el departamento de La Paz (Bolivia), situado en las coordenadas
aproximadas 16,05° S y 68,30° O (Figura 1). Se trata de un glaciar de pequeño
tamaño y pendiente moderada, representativo de los cuerpos de hielo de la
cordillera. El área
de análisis está delimitada por la huella del DSM de referencia, de
0,96 km × 0,98 km (≈0,94 km²), y se distribuye entre ≈4.915 y ≈5.283 m s.n.m.

El polígono del glaciar correspondiente a 2017 tiene un área proyectada de
0,184 km² (18,4 ha) y se extiende entre ≈5.035 y ≈5.272 m s.n.m., con una
mediana de ≈5.174 m (calculada sobre el DSM de 2017). La masa de hielo presenta
una geometría compacta y de pendiente moderada, con un afloramiento rocoso
interno (nunatak) en su sector central-sur, visible como una laguna en los mapas
de diferencia de elevación (Figura 6).

El terreno estable utilizado como control está definido por un polígono de
0,041 km² (4,1 ha) que se organiza en cinco franjas de anchura métrica
dispuestas en el perímetro del glaciar (Figura 1); su extensión equivale al
22 % del área del glaciar y su diámetro máximo es de ≈1 km. Esta configuración
—control periférico, estrecho y fragmentado— es característica de los
levantamientos con dron, en los que el polígono de glaciar cubre casi toda la
zona útil del vuelo.

![Figura 1. Área de estudio.](figures/F1_polygons_overview.png)

**Figura 1.** Vista general del área de análisis en la cuadrícula del DSM de
referencia (2025). En verde, el polígono de terreno estable empleado como
control del co-registro y del deramp; en rojo, el polígono del glaciar en 2017
(0,184 km²). El afloramiento rocoso interno del glaciar aparece como una laguna
blanca en el polígono rojo.

---

## 3. Datos

### 3.1 DSM y cuadrícula de referencia

Se utilizaron cuatro DSM derivados de fotogrametría con dron correspondientes a
2017, 2018, 2023 y 2025_B del Glaciar Llojeta. El DSM de 2025 se adoptó como referencia y define la
cuadrícula maestra del análisis: proyección UTM de la zona 19S (EPSG:32719),
resolución de 0,1 m y 9.780 × 9.591 píxeles. Todos los DSM fueron remuestreados
por el procedimiento de alineación del paso 0 del *pipeline* a esa cuadrícula,
de manera que las diferencias se calculan píxel a píxel sin interpolación
adicional ni desplazamientos por cambio de grilla.

Los DSM originales no se incluyen en el repositorio del proyecto por su tamaño;
el conjunto de datos de entrada y el procedimiento completo quedan descritos
por la configuración versionada (`config.toml`) y por las rutas locales
declaradas en `config.local.toml`. La fecha exacta de cada vuelo no está
registrada en el repositorio; los años se tratan como épocas anuales y las tasas
se calculan con denominadores de 8, 7 y 2 años para 2017, 2018 y 2023,
respectivamente.

### 3.2 Polígonos de apoyo

Se emplearon dos polígonos vectoriales, ambos versionados en el repositorio
(`data/`):

- `glaciar_2017.gpkg`: contorno del glaciar en 2017 (0,184 km²), utilizado como
  dominio de integración del DoD en todos los años. Al mantener fijo el dominio,
  los volúmenes de los tres años son comparables entre sí.
- `stable_terrain.gpkg`: terreno estable (0,041 km²) en cinco franjas
  perimetrales, utilizado como máscara de calibración del co-registro, del
  deramp y de la validación cruzada.

Ambos polígonos están en EPSG:32719 y son validados en tiempo de ejecución
(coherencia de CRS e intersección con el ráster de referencia) antes de usarse
como máscara.

---

## 4. Métodos

### 4.1 Co-registro Nuth & Kääb

Cada DSM fue co-registrado al DSM de 2025 con el algoritmo de Nuth & Kääb (2011)
en su implementación de `xdem` (`NuthKaab`), restringiendo el ajuste a los
píxeles finitos del terreno estable y con un submuestreo del 20 % de los
píxeles para acotar el coste computacional. El algoritmo estima iterativamente
un desplazamiento horizontal (este, norte) por correlación de la señal de
pendiente y un desplazamiento vertical por la mediana de las diferencias, hasta
converger; el resultado se aplica a la totalidad del DEM del año.

La calidad del co-registro se evalúa sobre la misma máscara estable con dos
estadísticos robustos: la mediana del residual y el NMAD (*normalized median
absolute deviation*), definido como 1,4826 veces la desviación absoluta mediana.
El NMAD se prefiere a la desviación estándar porque es insensible a los valores
extremos asociados a bordes de máscara, sombras y píxeles de hielo mal
clasificados.

### 4.2 Deramp polinómico de grado 3

Sobre el DEM ya co-registrado se ajustó un polinomio bidimensional completo de
grado 3 en las coordenadas de la cuadrícula. La base es un producto tensorial de
16 términos (todas las combinaciones *xⁱ yʲ* con 0 ≤ i, j ≤ 3), equivalente a la
que resuelve `numpy.polynomial.polynomial.polyval2d` y a la que emplea
`xdem.coreg.Deramp` para el deramp polinómico. El ajuste se realiza por mínimos
cuadrados ordinarios sobre los residuales (DEM<sub>2025</sub> −
DEM<sub>año,NK</sub>) del terreno estable, y el campo resultante se aplica al DEM
completo del año. Para evitar varias copias del DEM completo en memoria
(94 millones de píxeles, ≈0,4 GB por copia en *float32*), el polinomio se aplica
por bloques de 256 filas, de modo que el resultado es idéntico al de una
evaluación global pero con un uso de memoria acotado; la equivalencia con
`xdem.coreg.Deramp` se verifica numéricamente en las pruebas del repositorio.

Se generaron así dos variantes adicionales por año: `deramp3` (corrección
ajustada y aplicada sin validación) y `derampCV` (corrección aceptada o
rechazada según el criterio de la sección 4.3).

### 4.3 Validación cruzada espacial bloqueada

La decisión de aplicar o no el deramp se sometió a una validación cruzada
espacial *leave-one-block-out*. La extensión del terreno estable se dividió en
una grilla de 4 × 4 bloques; en cada iteración se retiene un bloque como
conjunto de prueba (>2.000 píxeles), se ajusta el polinomio sobre los píxeles de
los bloques restantes (con un máximo de 200.000 píxeles de entrenamiento,
submuestreados sin reemplazo con semilla 42) y se evalúa el NMAD de los
residuales en el bloque retenido. De los 16 bloques, 11 superaron el mínimo de
píxeles y se utilizaron como folds.

El criterio de aceptación compara, sobre los mismos folds y por tanto libres de
autocorrelación espacial entre entrenamiento y prueba, el NMAD del deramp con el
del DEM co-registrado sin deramp: el deramp se acepta únicamente si reduce el
NMAD fuera de muestra. Este criterio es más exigente que la comparación
*in-sample*, que siempre favorece al polinomio porque añade 16 parámetros
ajustados con los mismos datos que luego se evalúan.

La validación cruzada se implementó de forma vectorizada con
`numpy.linalg.lstsq` sobre una matriz de diseño polinómica construida
explícitamente, en lugar de aplicar `xdem.coreg.Deramp` sobre el DEM completo en
cada fold. La equivalencia matemática con `xdem` (misma base de términos, mismos
mínimos cuadrados) está verificada por una prueba ejecutable del repositorio, y
la reimplementación evita las copias temporales del DEM que, con 94 millones de
píxeles, agotaban la memoria disponible.

### 4.4 Diferencia de DEM y balance geodésico

El DoD se calculó como dH = DEM<sub>año</sub> − DEM<sub>2025</sub> sobre el
polígono del glaciar de 2017, en la cuadrícula de referencia y restringido a los
píxeles finitos en ambos DEM. Con esta convención, un dH positivo indica que la
superficie era más alta en el año comparado que en 2025 y, por tanto, que hubo
pérdida de masa entre ambas fechas.

Se definieron tres conjuntos de resultados. La **Opción B** (principal) usa la
variante NK para los tres años, lo que garantiza consistencia metodológica entre
épocas. La **Opción A** usa, para cada año, la variante aceptada por la
validación cruzada de la sección 4.3, de modo que coincide con la Opción B si el
deramp no es aceptado en ningún año. La **Opción C** (sensibilidad) aplica el
deramp3 en todos los años, es decir, el resultado que se obtendría adoptando la
corrección por convención y sin verificación; su diferencia con la Opción B
delimita la sensibilidad metodológica del volumen.

El volumen de cambio se obtuvo como Σ dH · A<sub>px</sub>, con
A<sub>px</sub> = 0,01 m², y se reporta junto con la media, la mediana, el NMAD y
los percentiles 5 y 95 de dH, además del área efectiva de integración de cada
año. Para expresar los resultados como tasa, el volumen se dividió por el número
de años transcurridos.

### 4.5 Propagación de la incertidumbre

La incertidumbre del volumen se propagó como error aleatorio de la media
espacial (Rolstad et al., 2009):

σ<sub>V</sub> = σ<sub>ruido</sub> · A / √N<sub>eff</sub>, con N<sub>eff</sub> = A / L²

donde A es el área de integración, σ<sub>ruido</sub> el nivel de ruido del
co-registro —medido como NMAD del residual sobre terreno estable, no sobre el
glaciar— y L la longitud de correlación de ese mismo residual. De este modo la
expresión puede reescribirse como σ<sub>V</sub> ≈ σ<sub>ruido</sub> · L · √A, en
la que el error del volumen crece con la amplitud del ruido, con su escala de
correlación y con la raíz del área integrada.

Es importante distinguir σ<sub>ruido</sub> de la dispersión de dH sobre el
glaciar (NMAD de 1,7–3,2 m, sección 5.3): esta última refleja la variabilidad
espacial real del adelgazamiento y no el error de medición, de modo que usarla
como término de error sobrestimaría la incertidumbre en dos órdenes de
magnitud. La longitud de correlación L se estimó con el variograma experimental
del residual de co-registro en terreno estable, calculado con desplazamientos
diagonales de hasta 50 píxeles y ajustado con un modelo exponencial o esférico
por mínimos cuadrados no lineales; para el modelo exponencial se usa el rango
práctico (3*a*). Si el variograma no converge se recurre a la fracción
arbitraria del 5 % de píxeles efectivos, caso que el *pipeline* registra
explícitamente en la tabla de resultados.

### 4.6 Implementación y reproducibilidad

Todo el análisis se implementó en Python 3.12 sobre un paquete propio (`nkdem`)
y un *pipeline* de cinco pasos ejecutables en orden (`00`–`05`). Las
dependencias principales son `numpy` (Harris et al., 2020), `scipy` (Virtanen et
al., 2020), `rasterio`, `geopandas`, `matplotlib` (Hunter, 2007) y `xdem`
0.2.3, que implementa el co-registro Nuth & Kääb y el deramp polinómico de
referencia. Los parámetros metodológicos están centralizados en un archivo de
configuración versionado, las rutas de los datos de entrada se declaran fuera
del código y las pruebas unitarias (28 pruebas) cubren la configuración, los
estadísticos, la equivalencia de la validación cruzada con `xdem`, el estimador
de N<sub>eff</sub>, la validación de CRS de los polígonos, la semántica del
ajuste del deramp y la implementación del deramp por bloques.

---

## 5. Resultados

### 5.1 Co-registro en el terreno estable

El co-registro de Nuth & Kääb redujo la mediana del residual a valores
inferiores a 1 mm en los tres años (Tabla 1), de modo que el desplazamiento
vertical residual es despreciable frente al NMAD. El NMAD del residual sobre
terreno estable fue de 0,471 m (2017), 0,372 m (2018) y 0,143 m (2023): la
calidad del ajuste mejora marcadamente con la cercanía temporal a la referencia.

**Tabla 1.** Co-registro y variantes de deramp sobre terreno estable
(n = píxeles válidos de la máscara común).

| Año | n | NMAD NK (m) | Mediana NK (m) | NMAD deramp3 (m) | NMAD CV deramp3 (m) | NMAD CV NK (m) | CV acepta |
|---|---|---|---|---|---|---|---|
| 2017 | 3.916.452 | 0,471 | +0,001 | 0,411 | 0,486 | 0,449 | No |
| 2018 | 4.055.566 | 0,372 | 0,000 | 0,321 | 0,359 | 0,359 | No |
| 2023 | 4.055.566 | 0,143 | 0,000 | 0,211 | 0,251 | 0,143 | No |

La distribución de los residuales es simétrica y centrada en cero (Figura 2),
sin colas gruesas que sugieran contaminación por píxeles de hielo o de borde.
Los mapas de residual (Figura 3), en cambio, muestran estructura espacial:
gradientes de hasta 2–3 m a lo largo de las franjas de control, con la
configuración más heterogénea en 2017 y la más homogénea en 2023. Esa estructura
—y no la magnitud global del desplazamiento— es la que el deramp intenta
absorber.

![Figura 2. Histogramas de residual NK.](figures/F2_residuals_nk_hist.png)

**Figura 2.** Distribución del residual (DEM<sub>año</sub> − DEM<sub>2025</sub>)
en el terreno estable tras el co-registro Nuth & Kääb, por año.

![Figura 3. Mapas de residual NK.](figures/F3_residuals_nk_map.png)

**Figura 3.** Estructura espacial del residual de co-registro en el terreno
estable. Las franjas perimetrales muestran gradientes internos de hasta 2–3 m,
que constituyen la señal que el deramp polinómico modela.

### 5.2 Deramp: mejora *in-sample* sin ganancia fuera de muestra

El deramp de grado 3 mejoró el NMAD *in-sample* en 2017 (0,471 → 0,411 m,
−13 %) y en 2018 (0,372 → 0,321 m, −14 %), pero lo empeoró en 2023
(0,143 → 0,211 m, +48 %). La validación cruzada espacial, sin embargo, fue
consistentemente desfavorable en los tres años: el NMAD fuera de muestra del
deramp fue de 0,486, 0,359 y 0,251 m, frente a 0,449, 0,359 y 0,143 m del DEM
co-registrado sin deramp (Tabla 1). El criterio de aceptación —reducir el NMAD
fuera de muestra— no se cumplió en ningún año, de modo que la variante adoptada
por la validación cruzada fue NK en los tres casos y la Opción A coincide
numéricamente con la Opción B (sección 5.5).

La discrepancia entre la mejora *in-sample* y la ausencia de ganancia fuera de
muestra es el resultado metodológico central de este trabajo, y su origen es
visible en el campo de corrección de 2018 (Figura 4): sobre el terreno estable,
donde existen datos, la corrección polinómica es prácticamente nula (media
+0,128 m; mediana +0,052 m); sobre el glaciar, donde no los hay, alcanza
−1,119 m de media (mediana −1,193 m) y oscila entre −2,119 m (P5) y +0,208 m
(P95). La corrección no describe una deformación observada en el glaciar, sino
una extrapolación de gran amplitud desde un control periférico en el que la
deformación es ~0.

La corrección no muestra sesgo direccional respecto de la pendiente ni de la
orientación (coeficiente de Spearman entre corrección y pendiente = −0,046;
Figura 5): el campo es un domo suave, coherente con un polinomio de grado 3
extrapolado, y no con una dependencia física de la geometría del terreno.

![Figura 4. Campo de corrección del deramp3 en 2018.](figures/F4_deramp_correction_map_2018.png)

**Figura 4.** Campo de corrección aplicado por el deramp3 en 2018 (deramp3 − NK;
rojo = resta, azul = suma). La corrección es nula en las franjas de terreno
estable y alcanza −1 a −2,2 m en el interior del glaciar, donde no existe
control que la respalde. El histograma de la derecha compara la distribución de
la corrección en terreno estable y en el glaciar.

![Figura 5. Corrección del deramp3 frente a pendiente y orientación (2018).](figures/F5_deramp_vs_slope_aspect.png)

**Figura 5.** Corrección del deramp3 en 2018 frente a la pendiente (izquierda;
puntos = media por clase, barras = desviación estándar) y a la orientación de la
ladera (derecha). El campo de corrección es aproximadamente constante
(≈−1 m) en todo el rango de pendientes y orientaciones, sin sesgo direccional
apreciable (ρ de Spearman = −0,046).

### 5.3 Cambio de elevación y volumen

Sobre el polígono del glaciar de 2017, el cambio de elevación mediano fue de
+9,472 m (2017), +8,799 m (2018) y +4,417 m (2023), y la media de +9,756,
+8,933 y +4,007 m (Tabla 2). Todos los valores son positivos con la convención
adoptada (dH = DEM<sub>año</sub> − DEM<sub>2025</sub>), es decir, la superficie
era más alta en los años comparados que en 2025 y el glaciar perdió masa en el
intervalo.

**Tabla 2.** DoD sobre el glaciar 2017 con la variante NK (Opción B). dH > 0
indica pérdida de masa entre el año y 2025. σ<sub>V</sub>: incertidumbre del
volumen por ruido del co-registro (sección 5.6).

| Año | N píxeles | Área (km²) | dH media (m) | dH mediana (m) | NMAD (m) | P5 (m) | P95 (m) | Volumen (10⁶ m³) | σ<sub>V</sub> (m³) |
|---|---|---|---|---|---|---|---|---|---|
| 2017 | 17.946.854 | 0,1795 | +9,756 | +9,472 | 3,237 | +3,145 | +16,231 | +1,751 | 1.651 |
| 2018 | 17.593.665 | 0,1759 | +8,933 | +8,799 | 3,214 | +1,629 | +14,873 | +1,572 | 618 |
| 2023 | 18.423.275 | 0,1842 | +4,007 | +4,417 | 1,725 | +0,039 | +7,312 | +0,738 | 437 |

A partir de estos valores y del intervalo transcurrido entre cada par de fechas
se obtienen las tasas de la Tabla 3. El adelgazamiento medio fue de 1,22 m a⁻¹
para 2017–2025 y de 1,28 m a⁻¹ para 2018–2025, y asciende a 2,00 m a⁻¹ para
2023–2025. Con una densidad de conversión de 850 kg m⁻³ (Huss, 2013), el
balance específico geodésico equivalente es de 1,04, 1,09 y 1,70 m w.e. a⁻¹,
respectivamente.

**Tabla 3.** Tasas derivadas del DoD de la Tabla 2.

| Año | Δt (a) | dH media (m) | Adelgazamiento (m a⁻¹) | Volumen (10⁶ m³) | Tasa de volumen (10³ m³ a⁻¹) | Balance específico (m w.e. a⁻¹) |
|---|---|---|---|---|---|---|
| 2017 | 8 | +9,756 | 1,22 | +1,751 | 219 | 1,04 |
| 2018 | 7 | +8,933 | 1,28 | +1,572 | 225 | 1,09 |
| 2023 | 2 | +4,007 | 2,00 | +0,738 | 369 | 1,70 |

La dispersión de dH sobre el glaciar (NMAD de 3,24, 3,21 y 1,73 m) es un orden de
magnitud mayor que el ruido del co-registro (0,47, 0,37 y 0,14 m): refleja la
variabilidad espacial real del adelgazamiento y no la precisión de la medición.
Los histogramas (Figura 7) son bimodales: un pico estrecho en dH ≈ 0, que reúne
el afloramiento rocoso interno y los píxeles de borde del polígono, y una moda
principal en 4–10 m que concentra el adelgazamiento, con cola hacia valores
altos. El mapa de 2017 (Figura 6) muestra los valores máximos en el sector
occidental y centro-sur de la masa de hielo.

![Figura 6. Mapas del DoD.](figures/F6_dod_maps.png)

**Figura 6.** Mapas de la diferencia de elevación sobre el polígono del glaciar
2017 para los tres años (Opción B). Los valores positivos indican que la
superficie era más alta en el año comparado que en 2025, es decir, pérdida de
masa. El anillo perimetral de valores bajos está asociado al borde del polígono
y al afloramiento rocoso interno.

![Figura 7. Histogramas del DoD.](figures/F7_dod_histograms.png)

**Figura 7.** Distribuciones del cambio de elevación por año sobre el glaciar
2017 (Opción B).

### 5.4 Patrón espacial e hipsometría

El adelgazamiento no es uniforme. En los tres años se observa (i) un máximo en
el sector medio-bajo del glaciar, (ii) una disminución hacia la cabecera y
(iii) valores próximos a cero en el afloramiento rocoso interno y en el anillo
perimetral del polígono (Figura 6). La hipsometría del cambio (Figura 8) lo
cuantifica: el dH mediano alcanza ≈16 m en 2017 y ≈14,7 m en 2018 en las franjas
de 5.040–5.070 m, y desciende a ≈7,2 m y ≈5,6 m en las franjas superiores
(≈5.250 m). En 2023 el máximo se sitúa algo más abajo (≈6,8 m hacia 5.040 m) y
la disminución con la altitud es más suave.

![Figura 8. Hipsometría del cambio.](figures/F8_dod_hypsometry.png)

**Figura 8.** dH mediano por franja altitudinal de 20 clases sobre el DEM de
2025 (Opción B). El adelgazamiento es máximo en el sector medio-bajo y decrece
hacia la cabecera.

### 5.5 Sensibilidad a la variante de co-registro

Dado que la validación cruzada rechazó el deramp en los tres años, la Opción A
coincide exactamente con la Opción B (ΔV = 0 en todos los años). Para
cuantificar el efecto que tendría adoptar el deramp sin verificación se calculó
la Opción C, en la que el deramp3 se aplica en todos los años (Figura 9,
Tabla 4). El volumen se reduce en 0,091 × 10⁶ m³ en 2017 (−5,2 %), 0,197 × 10⁶ m³
en 2018 (−12,5 %) y 0,039 × 10⁶ m³ en 2023 (−5,3 %); en términos de dH medio, la
corrección forzada resta 0,508, 1,119 y 0,212 m.

**Tabla 4.** Sensibilidad del volumen a la variante de co-registro.

| Año | V Opción B (10⁶ m³) | V Opción C (10⁶ m³) | ΔV (10⁶ m³) | ΔV (%) | ΔdH media (m) |
|---|---|---|---|---|---|
| 2017 | +1,751 | +1,660 | −0,091 | −5,2 | −0,508 |
| 2018 | +1,572 | +1,375 | −0,197 | −12,5 | −1,119 |
| 2023 | +0,738 | +0,699 | −0,039 | −5,3 | −0,212 |

![Figura 9. Sensibilidad a la variante de co-registro.](figures/F9_sensitivity_B_vs_A.png)

**Figura 9.** Volúmenes de cambio por opción: B (todo NK), A (variante aceptada
por la validación cruzada, idéntica a B) y C (deramp3 forzado en todos los
años). Los porcentajes indican la diferencia de C respecto de B.

### 5.6 Incertidumbre del volumen

El modelo de ruido del co-registro (Tabla 5) arroja longitudes de correlación de
4,0–8,3 m, muy inferiores a la extensión del glaciar, de modo que el número
efectivo de píxeles independientes es de 2,6 × 10³ a 1,1 × 10⁴. Con esos valores,
la incertidumbre aleatoria del volumen es de 1.651, 618 y 437 m³, es decir,
0,09 %, 0,04 % y 0,06 % del volumen estimado. Ninguno de los tres años requirió
el *fallback* de fracción arbitraria: el variograma convergió en todos los casos
con un modelo exponencial.

**Tabla 5.** Modelo de ruido del co-registro en terreno estable y propagación de
la incertidumbre del volumen.

| Año | σ<sub>ruido</sub> (m) | Rango L (m) | Modelo | N<sub>eff</sub> (glaciar) | σ<sub>V</sub> (m³) | σ<sub>V</sub> (%) |
|---|---|---|---|---|---|---|
| 2017 | 0,471 | 8,3 | exponencial | 2.623 | 1.651 | 0,09 |
| 2018 | 0,372 | 4,0 | exponencial | 11.222 | 618 | 0,04 |
| 2023 | 0,143 | 7,1 | exponencial | 3.615 | 437 | 0,06 |

---

## 6. Discusión

### 6.1 Magnitud y ritmo del adelgazamiento

Los volúmenes estimados (+1,75, +1,57 y +0,74 × 10⁶ m³) implican una pérdida de
masa sostenida durante el período analizado, con un balance específico
geodésico de 1,0–1,7 m w.e. a⁻¹. Estas tasas son del orden de magnitud de las
reportadas para glaciares de los Andes tropicales en las últimas dos décadas
(Hugonnet et al., 2021; Zemp et al., 2019), aunque la comparación es
necesariamente cualitativa: se trata de un glaciar pequeño, con un área de
0,18 km², para el que no se dispone de series de balance de masa *in situ* con
las que contrastar el resultado geodésico.

La comparación entre intervalos sugiere una aceleración del adelgazamiento
(1,22 m a⁻¹ en 2017–2025 frente a 2,00 m a⁻¹ en 2023–2025). Esa lectura debe
tomarse con cautela por tres motivos: (i) los intervalos comparados tienen
duraciones muy distintas (8 y 2 años), de modo que el segundo está mucho más
expuesto a la variabilidad interanual; (ii) todos los años se comparan contra la
misma referencia de 2025, por lo que los errores de esa referencia son comunes a
las tres estimaciones y no se cancelan al compararlas entre sí; y (iii) con
cuatro épocas no es posible separar tendencia de variabilidad. El patrón
altitudinal (secciones 5.4 y 6.3) es, en cambio, consistente entre años y aporta
una señal más robusta que la sola comparación de tasas.

### 6.2 El deramp como extrapolación: por qué la validación cruzada lo rechaza

El resultado más relevante de este trabajo no es el volumen, sino la
demostración empírica de que un deramp polinómico puede mejorar el ajuste
*in-sample* y, al mismo tiempo, no aportar ninguna ganancia fuera de muestra. En
2017 y 2018 el polinomio redujo el NMAD sobre el terreno de control en un
13–14 %, pero al evaluarlo en bloques espaciales no vistos el NMAD no mejoró (o
empeoró claramente); el criterio de aceptación lo rechazó en los tres años.

La explicación es geométrica y se ve en la Figura 4: el terreno estable rodea al
glaciar en franjas estrechas, de modo que el polinomio está bien determinado en
el borde y mal determinado en el interior. Con 16 parámetros y un control
periférico, el ajuste interpola el ruido de las franjas y extrapola al centro
una superficie suave sin respaldo observacional. En 2018 esa extrapolación vale
−1,1 m de media, equivalente al 12,5 % del volumen estimado y muy superior
al NMAD del co-registro (0,37 m). El diagnóstico de la Figura 5 descarta que se
trate de una corrección físicamente estructurada (no hay dependencia con
pendiente ni orientación), lo que refuerza la interpretación de que es un
artefacto del ajuste y no una deformación del DSM.

Este resultado tiene una consecuencia práctica inmediata: en glaciares pequeños
con control periférico escaso, adoptar el deramp por convención introduce un
sesgo de hasta el 12 % en el volumen, del mismo orden que el error sistemático
que se pretende corregir. La validación cruzada espacial, en cambio, convierte
esa decisión en una prueba explícita y reproducible, y en este caso la respuesta
es que la corrección no debe aplicarse.

### 6.3 Patrón altitudinal

El máximo de adelgazamiento en el sector medio-bajo (≈5.040–5.100 m) y su
disminución hacia la cabecera son coherentes con un glaciar de pendiente
moderada en el que la ablación se concentra en las zonas más bajas y expuestas,
mientras la parte alta mantiene una cobertura nival o de hielo más persistente.
La similitud del patrón entre 2017, 2018 y 2023 —a pesar de las diferencias de
magnitud— sugiere que la estructura espacial del balance es estable en el
tiempo, una observación que no depende de la magnitud absoluta del volumen y que
por tanto es más robusta frente a los errores sistemáticos.

Los valores próximos a cero en el anillo perimetral del polígono (Figura 6) no
deben interpretarse como ausencia de cambio: corresponden al borde de la máscara
de 2017, donde la diferencia de elevación mezcla hielo, roca y nieve estacional y
donde el DSM de 2025 puede no representar la misma superficie que en 2017. Por
esa razón el volumen se integra sobre el polígono completo pero la interpretación
espacial se restringe al interior de la masa de hielo.

### 6.4 Componentes de la incertidumbre

La incertidumbre aleatoria propagada desde el ruido del co-registro es
despreciable (0,04–0,09 %). Ello no significa que el volumen esté determinado con
esa precisión: los términos dominantes son sistemáticos y no están incluidos en
esa propagación. Los principales son:

1. **Elección de variante.** Cuantificada en la Tabla 4: −5,2 %, −12,5 % y −5,3 %
   si se adopta el deramp forzado. La validación cruzada indica que esa variante
   no está respaldada por los datos, pero el ejercicio delimita el rango de
   sensibilidad metodológica.
2. **Densidad de conversión.** El paso de volumen a masa con 850 kg m⁻³ (Huss,
   2013) asume una densidad media del hielo/firn perdido; un rango plausible de
   800–900 kg m⁻³ desplaza el balance específico en ∓6 %.
3. **Máscara y área de integración.** El polígono se mantiene fijo en su
   contorno de 2017, lo que garantiza comparabilidad entre años pero incluye
   píxeles de borde y de afloramiento rocoso, y no contabiliza la reducción del
   área glaciar.
4. **Exactitud absoluta de los DSM.** No se dispone de datos de control
   diferencial (GNSS) para cuantificar el error vertical absoluto de cada vuelo;
   el NMAD en terreno estable mide la consistencia relativa entre DSM, no su
   exactitud individual.
5. **Diferencias de penetración y estacionalidad.** Sin las fechas exactas de
   cada vuelo no puede descartarse que parte de la diferencia de elevación
   corresponda a nieve estacional en lugar de hielo.

Una estimación realista de la incertidumbre total se sitúa por tanto en el orden
del 10–15 % del volumen, dominada por los términos sistemáticos 1–2 y no por el
error aleatorio.

### 6.5 Limitaciones

Las limitaciones del estudio son las de su configuración experimental: el
terreno estable disponible es pequeño (0,041 km², 22 % del área del glaciar),
estrecho y periférico, lo que limita la capacidad de detectar y corregir
deformaciones de baja frecuencia; el glaciar está cubierto en un 97 % por el
*convex hull* del terreno estable, con una distancia mediana de 128 m y máxima de
260 m, de modo que la extrapolación es inevitable aunque acotada; sólo se
dispone de cuatro épocas, sin las fechas exactas de vuelo; y no se cuenta con
mediciones independientes (GNSS, ablación, densidad) que permitan validar la
exactitud de los DSM. Los resultados deben leerse, en consecuencia, como una
estimación robusta de la magnitud del cambio y de su estructura espacial, con una
incertidumbre sistemática del orden del 10–15 %, y no como un balance de masa con
precisión de unos pocos por ciento.

---

## 7. Conclusiones

1. El co-registro de Nuth & Kääb alineó los tres DSM a la referencia de 2025 con
   un NMAD residual sobre terreno estable de 0,471, 0,372 y 0,143 m (2017, 2018
   y 2023), sin desplazamiento vertical residual apreciable.

2. El deramp polinómico de grado 3 mejoró el ajuste *in-sample* en 2017 y 2018
   (hasta un 14 %), pero la validación cruzada espacial bloqueada no encontró
   ganancia fuera de muestra en ningún año, por lo que fue rechazado en los tres
   casos. Esta discrepancia, y no el ajuste aparente, es el criterio que debe
   gobernar la decisión de corregir.

3. La corrección de 2018 es nula sobre el terreno de control (+0,13 m de media) y
   alcanza −1,1 m de media en el interior del glaciar: es una extrapolación, no
   una deformación observada. Aplicarla sin verificación reduciría el volumen de
   2018 en un 12,5 % (0,197 × 10⁶ m³).

4. El glaciar perdió 1,751 × 10⁶, 1,572 × 10⁶ y 0,738 × 10⁶ m³ de hielo entre
   2017, 2018 y 2023 y 2025, respectivamente (Opción B, todo NK), equivalentes a
   un adelgazamiento medio de 1,22, 1,28 y 2,00 m a⁻¹ y a un balance específico
   de 1,04, 1,09 y 1,70 m w.e. a⁻¹ (ρ = 850 kg m⁻³).

5. El adelgazamiento es máximo en el sector medio-bajo (≈5.040–5.100 m) y decrece
   hacia la cabecera, con un patrón espacial estable entre años.

6. La incertidumbre aleatoria del volumen, propagada desde el ruido del
   co-registro y su longitud de correlación, es inferior al 0,1 %; la
   incertidumbre total está dominada por términos sistemáticos (variante de
   corrección, densidad, máscara) y se estima en el 10–15 %.

---

## Disponibilidad de datos y código

El *pipeline* completo (pasos 00–05), los polígonos de apoyo y las pruebas
unitarias (28) están en <https://github.com/eguivarjosed48-dot/NK-native>. Los
DSM de entrada no se distribuyen por su tamaño; las rutas se declaran en un
archivo de configuración local. Los resultados intermedios (DEM co-registrados,
DoD en GeoTIFF, tablas y figuras) son regenerables ejecutando los scripts en
orden. El co-registro y el balance de masa en resolución original también se
publican, como etapas independientes del mismo estudio, en
<https://github.com/eguivarjosed48-dot/llojeta-coregistration-pipeline> y
<https://github.com/eguivarjosed48-dot/llojeta-dod-pipeline>.

## Agradecimientos

Se agradece el trabajo de campo y de procesamiento fotogramétrico que hizo
posible la serie de DSM utilizada. El análisis se apoya en el ecosistema de
código abierto `xdem`/`geoutils`, `rasterio`, `geopandas`, `numpy`, `scipy` y
`matplotlib`.

## Referencias

GlacioHack (2024). *xDEM: analysis of digital elevation models in Python*
(versión 0.2.3) [software]. https://github.com/GlacioHack/xdem

Harris, C. R., Millman, K. J., van der Walt, S. J., et al. (2020). Array
programming with NumPy. *Nature*, 585, 357–362.

Hugonnet, R., McNabb, R., Berthier, E., et al. (2021). Accelerated global glacier
mass loss in the early twenty-first century. *Nature*, 592, 726–731.

Hunter, J. D. (2007). Matplotlib: a 2D graphics environment. *Computing in
Science & Engineering*, 9(3), 90–95.

Huss, M. (2013). Density assumptions for converting geodetic glacier volume
change to mass change. *The Cryosphere*, 7, 877–887.

Nuth, C., & Kääb, A. (2011). Co-registration and bias corrections of satellite
elevation data sets for quantifying glacier thickness change. *The Cryosphere*,
5, 271–290.

Paul, F., Bolch, T., Kääb, A., et al. (2015). The glaciers climate change
initiative: methods for creating glacier area, elevation change and velocity
products. *Remote Sensing of Environment*, 162, 408–426.

Rolstad, C., Haug, T., & Denby, B. (2009). Spatially integrated geodetic glacier
mass balance and its uncertainty based on geostatistical analysis: application to
the western Svartisen ice cap, Norway. *Journal of Glaciology*, 55(192), 666–680.

Virtanen, P., Gommers, R., Oliphant, T. E., et al. (2020). SciPy 1.0: fundamental
algorithms for scientific computing in Python. *Nature Methods*, 17, 261–272.

Zemp, M., Huss, M., Thibert, E., et al. (2019). Global glacier mass changes and
their contributions to sea-level rise from 1961 to 2016. *Nature*, 568, 382–386.

---

## Apéndice A. Metadatos a completar antes del envío

Los siguientes elementos no están documentados en el repositorio y deben
completarse o verificarse por el autor antes de someter el manuscrito:

1. **Afiliación institucional** del autor (la versión actual indica «autor
   independiente»).
2. **Topónimo y cordillera**: se usa «Glaciar Llojeta (Cordillera Real, La Paz,
   Bolivia)», coherente con los repositorios previos del mismo estudio; conviene
   confirmar la denominación oficial/local y el macizo exacto antes del envío.
3. **Fechas exactas de cada vuelo** y sensor/cámara utilizados, así como el GSD
   efectivo y el error vertical absoluto declarado por el proveedor de los DSM.
4. **Densidad de conversión** empleada (aquí 850 kg m⁻³, Huss, 2013) o, si se
   dispone de ella, la densidad medida en el glaciar.
5. **Licencia y condiciones de uso** de los datos de entrada.
6. **Repositorio público** (URL de GitHub) para la declaración de disponibilidad
   de código.

