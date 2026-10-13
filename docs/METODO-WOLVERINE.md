# Método para optimizar Wolverine (PPSA03671), igual que Demon's Souls

Basado en el método que usó chenxiao07 para llevar Demon's Souls de ~21 a ~40 fps con Claude
(skill `.claude/skills/ps5-emu-optimization`, copiada de la rama `docs/ai-optimization-skill` de
chenxiao07/KytyPS5). Resumen y pasos aplicados a Wolverine.

## Dónde se va el tiempo (4 causas; identificar cuál antes de tocar código)
1. Un solo hilo traduce la cola gráfica (PM4) → cuello de botella. La GPU espera.
2. Coste fijo por draw/dispatch (tablas de recursos, búsquedas de buffers, descriptores, barreras).
3. Coherencia de memoria guest: protección de páginas, subidas, lecturas de la GPU que el juego espera.
4. Tirones (stutter): traducción de shaders y compilación de pipelines la primera vez, recreación de
   cachés tras unmap, esperas síncronas raras.

## Método (en orden)
1. Escena y métrica fijas: misma partida, mismo sitio, fps = fotogramas totales / tiempo; peor ventana de 1 s.
2. Perfilar el hilo de render con símbolos de ESE build y dividir el tiempo por tipo de trabajo.
3. Probar causalidad: inyectar un retardo conocido en el sitio; si el tiempo de fotograma no sube igual, ahí no se gana nada.
4. Medir el techo: versión insegura que se salta el trabajo. Si el techo es pequeño, no seguir.
5. Implementar detrás de un interruptor (KYTY_*), con modo verificación si sustituye trabajo de corrección.
6. A/B en el mismo proceso, alternando en caliente (live.txt) varias rondas en el mismo sitio.
7. Comprobar corrección: capturas, otra escena, partida larga sin cuelgue.
8. Quedarse o borrar: si no es claramente más rápido, se quita. Apuntar el resultado siempre.

## Reglas
- Solo optimizaciones lógicas que quitan trabajo real; nada de umbrales afinados por escena.
- Tasa de aciertos de una caché no es ahorro; contar el coste completo.
- Pasar trabajo a otro hilo casi nunca ayuda con tareas de 1-5 us.
- Diagnósticos gratis cuando están apagados; fps con instrumentación no cuentan.
- vblank a 60 Hz como la consola. Nunca experimentar con la partida del jugador.
- Prohibido hacer trampa: no subir KYTY_HITCH_LOG_MS, no quitar logs, no saltar fotogramas, no bajar resolución.

## Mejoras ya probadas en Demon's Souls (aplicar primero si faltan)
1. Grabación Vulkan en hilo aparte y submits diferidos (21 → 23,7 fps).
2. Registros nativos para draws repetidos (24,9 → 30,9 fps).
3. Lecturas de GPU que no esperan a toda la cola (+1,25 fps).
4. Seguimiento de páginas más barato (+1 fps y más).
5. Quitar barreras duplicadas (+1,4 %).
6. Compilación -O3, ThinLTO, PGO (+8 %).
Tirones:
7. Pipelines sin optimizar primero y la versión optimizada en segundo plano (tirones 22 s → 0).
8. Precompilación estática desde los archivos del juego (en Wolverine: aprender de lo jugado,
   porque los shaders no se leen igual).
9. Traductor con menos complejidad y SPIR-V determinista.
10. No recrear recursos grandes en unmap parcial.

## Pasos para Wolverine
- Paso 0 (hecho): línea "Frames (5 s)" con fps, media, p99, máximo, y tiempo en shaders y esperas de pipelines.
- Paso 1: medición de partida en la zona del principio del gameplay (5-15 fps, máximos de 0,5-5 s; ~800 PS nuevos).
- Paso 2: confirmar la causa con el desglose (tirones = compilación) y aplicar 7 (pipelines sin optimizar primero)
  y guardar el SPIR-V traducido entre partidas.
- Paso 3: perfil del hilo de render con símbolos; atacar el bloque mayor (1-6 de la lista).
- Paso 4: cada cambio con interruptor, A/B en el mismo proceso, tabla antes/después.
- Glitches apuntados: luna repetida varias veces en el cielo.
