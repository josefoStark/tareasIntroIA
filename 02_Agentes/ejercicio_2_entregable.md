# Ejercicio 2 — Descripción PEAS de agentes inteligentes


## Contexto

En el capítulo 2 de *Artificial Intelligence: A Modern Approach* (Russell & Norvig),
un agente se entiende mejor cuando se especifica su **entorno de tarea**. Una forma
estándar de hacerlo es la descripción **PEAS**:

| Letra | Significado | Pregunta guía |
|---|---|---|
| **P** | *Performance* (medida de desempeño) | ¿Cómo se evalúa el éxito del agente? |
| **E** | *Environment* (entorno) | ¿En qué mundo opera? ¿Quién más actúa ahí? |
| **A** | *Actuators* (actuadores) | ¿Qué acciones puede ejecutar? |
| **S** | *Sensors* (sensores) | ¿Qué información puede percibir? |

Este ejercicio **no requiere programar**. Consiste en analizar distintos tipos de
aplicaciones reales y describir cada una con el esquema PEAS.

## Objetivo

Para cada una de las **8 aplicaciones** listadas abajo, redacta una descripción
PEAS completa y coherente. Debes pensar como diseñador del agente: qué optimiza,
dónde actúa, con qué puede mover o modificar el mundo, y qué puede observar.


## Descripciones PEAS

1. **Aplicación:** Asistente virtual de voz.
    - **Performance:** Tiempo de respuesta, Respuesta acorde a la pregunta/peticion
    - **Environment:** Casa, oficina, ruido de gente. 
    - **Actuators:** Bocina, Apagadores inteligentes, 
    - **Sensors:** Microfono, sensor de humedad, sensor de proximidad.

    Enviroment es no deterministico, secuencial, estatico, discreto. Lo considere no deterministico ya que al manejarse por conversaciones interacciones con el usuario el resultado depende del feedback del usuario, secuencial porque depende de la instruccion que vaya dando el usuario, estatico porque la interaccion sucede con el suficiente tiempo para que procese la respuesta y discreto porque hay un limitado numero de acciones como encender luces, apagar cierto electromestico, contestar a cierta respuesta.

1. **Aplicación:** Robot aspirador doméstico.
    - **Performance:** Velocidad de aspirado (m2/min), Area limpiada (m2), numero de habitaciones aspiradas, horas de funcionamiento, consumo de energia
    - **Environment:** Piso, obstaculos como muebles, mascotas, personas)
    - **Actuators:** Aspirador, ruedas del robot
    - **Sensors:** Sensor de proximidad, sensor de recipiente de aspirado lleno.

    Enviroment es deterministico, secuencial, estatico, continuo. Secuencial porque depende de donde ha limpiado previamente para actualizar su estado, semidinamico porque el ambienre como cuarto sucio no cambia tan bruscamente como para no alcanzar a procesar la informacion, continuo porque hay muchas ubicaciones por donde podria estar

1. **Aplicación:** Sistema de recomendación de streaming.
    - **Performance:** Numero de programas recomendados que fueron vistos, minutos vistos de programas
    - **Environment:** Smart tv, roku, android, wifi, 
    - **Actuators:** Pantalla
    - **Sensors:** Control tb, touchscreen

    Enviroment es no deterministico, secuencial, estatico, discreto. No deterministico porque puede no acertar en su recomendacion, secuencial porque depende de los programas vistos, estatico, porque va actualizandose confome va usando el usuario, discreto porque hay un numero finito de recomendaciones


1. **Aplicación:** Vehículo autónomo en ciudad.
    - **Performance:** Tiempo de llegada a destino, numero de accidentes, numero de averias, nivel gasolina, kilometraje, infracciones de transito, temperatura interior
    - **Environment:** Calles, carreteras, avenidas, señales de transito, peatones, trafico, condiciones de lluvia, sol, retenes, accidentes de transito, instrucciones de usuario, android car 
    - **Actuators:** Acelerador, Freno, volante, control de AC, control de parabrisas, bocinas, control ventanas
    - **Sensors:** gps, sensores de proximidad, camara, microfono, touchscreen, sensor temperatura, velocimetro

    Enviroment es no deterministico, secuencial, dinamico, continuo. No deterministico porque es probable que hayan muchas situaciones imprevistas durante la conduccion, secuencial porque depende del estado inmediato anterior, como donde esta a que velocidad va si frena, acelera o cambia de direccion. Dinamico porque siempre hay variables cambiando rapidamente trafico, peatones. Continuo porque tiene valores continuos como velocidad

1. **Aplicación:** Agente de trading algorítmico en bolsa.

    - **Performance:** Ganancias, tiempo de inversion, monto de inversión, impuestos por pagar, numero de inversiones, 
    - **Environment:** Casas de bolsas, noticias de politica, reportes financieros de empresas, bancos, eventos climaticos
    - **Actuators:** Orden de compra/venta acciones
    - **Sensors:** API's de paginas de noticias/finanzas

    Enviroment es no deterministico, secuencial, dinamico, continuo. No determinisitico ya que no hay certeza en como fluye el mercado, secuencial porque cada orden de compra/venta depende del feedback de las inversiones anteriores, dinamico porque es un ambiente que cambia a cada momento, continuo por el valor monetario

1. **Aplicación:** Sistema de diagnóstico médico asistido por IA.

    - **Performance:** Numero de pacientes atendidos, numero de pacientes con mejoria, numero de enfermedades detectadas
    - **Environment:** Hospital, consultorio, personas enfermas, estudios de laboratorio, ultrasonidos, radiografias
    - **Actuators:** Bocina, Pantalla, 
    - **Sensors:** Microfono, teclado o touchscren, scanner

    Enviroment es no deterministico, episodico, estatico, discreto. No deterministico porque es posible que el diagnostico sea erroneo, episodico porque cada diagnostico es independiente, estatico porque los resultados de los estudios no cambian rapidamente, discreto porque hay un numero finito de estudios.

1. **Aplicación:** Dron de inspección de infraestructura.

    - **Performance:** Averias detectadas, tiempo de vuelo, consumo de bateria,
    - **Environment:** Construcciones en proceso, casas abandonadas, edificios con gente trabajando, materiales de construccion, cableado electrico, fugas de agua, cuerpos de agua (mares, rios
    - **Actuators:** Motor de helices
    - **Sensors:** Gps, sensor de proximidad, Camara de video, camara fotografica, giroscopio, acelerometro

    Enviroment es no deterministico, episodico, estatico, discreto. No determinisitico porque puede no detectar alguna averia, episodico porque cada evaluacion no depende de la anterior, estatico porque la averia no cambiaria en un lapso corto de tiempo, discreto porque el numero de inspecciones/averias es un valor enterol


1. **Aplicación:** Agente jugador de ajedrez.

    - **Performance:** Numero de movimientos, Partidas ganadas, Tiempo  jugado
    - **Environment:** Piezas de ajedrez, contrincantes, torneos
    - **Actuators:** Brazo robot
    - **Sensors:** Camara
    
    Enviroment es deterministico, secuencial, semidinamico, discreto. Porque los movimientos de las piezas siguen reglas especificas, secuencial porque cada jugada depende de la posicion anterior de las piezas del tablero, semidinamico porque en cada movimiento el contrincante va actualizando el tablero tambien aunque el tiempo de cambio no es demasiado rapido, discreto porque hay un numero finito de movimientos


