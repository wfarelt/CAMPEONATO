# PROYECTO: PLATAFORMA DE GESTIÓN DE CAMPEONATOS DE FÚTBOL 2.0

## 1. ROL Y OBJETIVO

Actúa como arquitecto de software senior, desarrollador experto en Python, Django, diseño UX/UI y aplicaciones web responsivas.

Debes rediseñar y evolucionar una aplicación web de gestión de campeonatos de fútbol que ya fue utilizada exitosamente en una competición real.

El sistema actual permitió completar el campeonato, pero presentó dificultades durante la organización de los playoffs. El principal problema fue que el administrador técnico debía crear manualmente las jornadas y los partidos de las fases finales, cuando estas operaciones deberían estar disponibles directamente para el organizador del campeonato.

El objetivo es desarrollar una nueva versión más moderna, minimalista, juvenil, escalable y modular, con una experiencia excelente tanto en computadoras como en dispositivos móviles.

No se trata solamente de cambiar los colores y las plantillas. Se debe mejorar la arquitectura, los procesos administrativos, la experiencia del usuario y la automatización de las competiciones.

Antes de modificar archivos, inspecciona el proyecto existente y presenta un diagnóstico de su arquitectura, modelos, aplicaciones, vistas, plantillas, permisos y funcionalidades.

No elimines funcionalidades existentes sin analizar previamente su utilidad y compatibilidad.

## 2. TECNOLOGÍAS OBLIGATORIAS

### Backend
- Python.
- Django.
- Django ORM.
- SQLite como base de datos inicial y de despliegue.
- Django Forms para formularios y validaciones.
- Vistas basadas en funciones (Function-Based Views), siempre que sean adecuadas para el módulo.
- Arquitectura modular mediante aplicaciones Django independientes.
- Sistema de autenticación y autorización de Django.

No introducir PostgreSQL como requisito.

### Frontend
- HTML5 semántico.
- Bootstrap 5.
- CSS3.
- JavaScript nativo.
- Bootstrap Icons.
- Plantillas Django.
- Fetch API cuando sea necesario para operaciones asíncronas.
- Animaciones CSS ligeras.

PROHIBICIONES:
- No utilizar Tailwind CSS.
- No instalar ni utilizar React.
- No instalar ni utilizar Vue.
- No utilizar Angular.
- No introducir frameworks JavaScript pesados sin una justificación técnica aprobada.
- No duplicar estilos que Bootstrap ya proporciona.
- No introducir dependencias innecesarias.

El frontend debe integrarse directamente con las plantillas de Django.

## 3. FILOSOFÍA DEL DISEÑO

Crear una interfaz juvenil, deportiva, moderna y minimalista.

La plataforma debe transmitir dinamismo, competencia, claridad y profesionalismo.

Características visuales:

- Diseño limpio y ordenado.
- Uso eficiente del espacio disponible.
- Tipografía moderna y legible.
- Tarjetas compactas.
- Bordes suaves.
- Sombras discretas.
- Iconografía coherente.
- Colores deportivos.
- Contraste adecuado.
- Jerarquía visual clara.
- Formularios sencillos.
- Tablas adaptables.
- Navegación intuitiva.
- Estados visuales para acciones, errores, confirmaciones y advertencias.

Evitar:
- Interfaces recargadas.
- Gradientes excesivos.
- Animaciones exageradas.
- Demasiadas tarjetas dentro de otras tarjetas.
- Botones innecesariamente grandes en escritorio.
- Tablas que desborden el ancho del celular.
- Formularios largos sin organización.
- Paneles administrativos con demasiadas opciones visibles simultáneamente.

### Identidad visual

Implementar un sistema de diseño mediante variables CSS:

- Color primario configurable.
- Color secundario configurable.
- Color de fondo.
- Color de superficies.
- Color de texto principal.
- Color de texto secundario.
- Colores de éxito, advertencia, error e información.
- Radio de bordes.
- Espaciados.
- Sombras.
- Duración de transiciones.

La identidad visual debe poder personalizarse para cada campeonato sin tener que modificar todas las plantillas.

Crear una apariencia deportiva juvenil, utilizando una combinación de verde, blanco y tonos oscuros como propuesta inicial. Los colores definitivos deben poder configurarse.

### Animaciones

Incorporar animaciones sutiles y funcionales:

- Aparición progresiva de tarjetas.
- Transiciones al pasar el cursor.
- Realimentación visual de botones.
- Indicadores de carga.
- Transiciones de apertura de menús.
- Animación discreta al actualizar resultados.
- Realce visual de equipos clasificados.
- Microinteracciones en formularios.

Las animaciones deben ser rápidas y no perjudicar el rendimiento.

Respetar la preferencia del sistema mediante `prefers-reduced-motion`.

## 4. DISEÑO RESPONSIVE: WEB Y MÓVIL

La aplicación debe desarrollarse con un enfoque mobile-first.

Debe funcionar correctamente en:

- Teléfonos Android.
- iPhone.
- Tablets.
- Portátiles.
- Computadoras de escritorio.

En móviles:
- Navegación compacta.
- Menú lateral o menú desplegable.
- Botones fáciles de tocar.
- Formularios organizados en una columna cuando corresponda.
- Tarjetas de partidos optimizadas para pantallas pequeñas.
- Tablas transformadas en tarjetas o con desplazamiento horizontal controlado.
- Acciones administrativas accesibles sin saturar la pantalla.
- Marcadores visibles y fáciles de leer.

En escritorio:
- Aprovechar el ancho disponible.
- Mostrar información complementaria cuando aporte valor.
- Utilizar paneles y tablas compactas.
- Mantener una jerarquía visual clara.

La interfaz pública debe ser accesible sin iniciar sesión cuando corresponda.

La versión inicial será una aplicación web responsive. Preparar una arquitectura que permita evolucionar hacia una PWA, con instalación en dispositivos y funcionalidades offline cuidadosamente delimitadas, sin implementarlas prematuramente.

## 5. ARQUITECTURA MODULAR

Organizar el proyecto mediante aplicaciones Django independientes y con responsabilidades claras.

Tomar como referencia la siguiente estructura, adaptándola al proyecto existente. La estructura actual del repositorio es el punto de partida: reutiliza las aplicaciones existentes cuando sus responsabilidades sean adecuadas. Crea, divide o renombra aplicaciones solo si la auditoría demuestra una necesidad concreta y describe el impacto y la migración correspondientes. No dupliques modelos ni lógica para ajustarte literalmente al ejemplo:

config/
    settings.py
    urls.py
    asgi.py
    wsgi.py

apps/
    core/
    users/
    tournaments/
    teams/
    players/
    matchdays/
    matches/
    standings/
    playoffs/
    payments/
    notifications/
    sponsors/

templates/
    base.html
    components/
    public/
    accounts/
    dashboard/

static/
    css/
    js/
    images/

Cada aplicación debe tener una responsabilidad bien definida.

### core
Configuración general, página principal, identidad visual, parámetros generales y utilidades compartidas.

### users
Usuarios, autenticación, perfiles, permisos y roles.

### tournaments
Creación y configuración de campeonatos, temporadas, reglamentos y estados.

### teams
Equipos participantes, escudos, colores y datos de contacto.

### players
Jugadores, información deportiva, dorsales y pertenencia a equipos.

### matchdays
Jornadas, calendario y agrupación de partidos.

### matches
Partidos, resultados, eventos, goles, tarjetas y otros acontecimientos.

### standings
Clasificación, estadísticas y criterios de desempate.

### playoffs
Configuración y administración de las fases eliminatorias.

### payments
Registro y seguimiento de pagos, inscripciones y otros conceptos relacionados con el campeonato, según las necesidades reales.

### notifications
Notificaciones internas y notificaciones push cuando estén configuradas.

### sponsors
Patrocinadores, logotipos y enlaces.

Esta estructura es una propuesta inicial, no una obligación de crear aplicaciones vacías. Evitar fragmentar excesivamente el proyecto.

No duplicar modelos ni lógica de negocio entre aplicaciones.

Las operaciones críticas deben residir en servicios de dominio reutilizables y transaccionales, en lugar de concentrarse exclusivamente en las vistas.

Por ejemplo:
- Creación de jornadas.
- Generación de partidos.
- Registro de resultados.
- Cálculo de clasificaciones.
- Determinación de equipos clasificados.
- Generación de cruces eliminatorios.

Mantener separadas las responsabilidades de modelos, formularios, vistas, servicios y plantillas.

## 6. SISTEMA DE USUARIOS Y PERMISOS

Implementar roles claramente diferenciados.

### Administrador de plataforma
- Gestionar la configuración general.
- Administrar usuarios y permisos globales.
- Supervisar campeonatos.
- Acceder a las herramientas técnicas necesarias.
- Resolver incidencias de configuración.

### Organizador del campeonato
- Crear y configurar su campeonato.
- Registrar equipos.
- Administrar jugadores, según los permisos concedidos.
- Crear jornadas y calendarios.
- Configurar las fases finales.
- Generar cruces de playoffs.
- Publicar jornadas.
- Registrar o autorizar resultados.
- Consultar estadísticas.
- Administrar la información pública de su competición.

### Árbitro o responsable de resultados
- Consultar los partidos asignados.
- Registrar resultados y acontecimientos cuando esté autorizado.
- No modificar la configuración general del campeonato.

### Delegado de equipo
- Consultar los datos de su equipo.
- Gestionar la información autorizada.
- Consultar partidos y resultados.

### Visitante
- Consultar información pública.
- Ver jornadas, resultados, clasificación, estadísticas, goleadores y fases finales.

Los permisos deben verificarse en el backend, no únicamente ocultando botones en el frontend.

Un organizador solo podrá administrar los campeonatos para los que tenga autorización.

Evitar que un usuario pueda modificar objetos de otro campeonato cambiando identificadores en una URL.

Utilizar las herramientas de permisos de Django y validaciones explícitas de pertenencia a cada campeonato.

## 7. MÓDULO DE CAMPEONATOS

Cada campeonato debe permitir configurar:

- Nombre.
- Temporada.
- Descripción.
- Logotipo.
- Colores.
- Reglamento.
- Fecha de inicio.
- Fecha de finalización prevista.
- Estado.
- Equipos participantes.
- Sistema de competición.
- Número de puntos por victoria, empate y derrota.
- Criterios de desempate.
- Cantidad de equipos que avanzan a la fase final.
- Reglas de las fases eliminatorias.

Estados propuestos:

- Configuración.
- Inscripciones.
- En curso.
- Finalizado.
- Suspendido.

La aplicación debe permitir administrar varios campeonatos sin mezclar sus equipos, jornadas, partidos, clasificaciones o permisos.

Toda consulta y operación debe respetar el campeonato correspondiente.

## 8. MÓDULO DE JORNADAS Y PARTIDOS

El organizador debe disponer de una interfaz sencilla para:

- Crear una jornada.
- Asignar un nombre.
- Establecer fecha y horario.
- Seleccionar la cancha.
- Agregar partidos.
- Seleccionar equipos.
- Modificar horarios.
- Reprogramar partidos.
- Publicar o despublicar la jornada.
- Registrar resultados.
- Consultar el estado de cada encuentro.

Los partidos deben contemplar estados como:

- Programado.
- En curso, si el seguimiento en vivo está habilitado.
- Finalizado.
- Suspendido.
- Aplazado.
- Cancelado.

No permitir que un mismo partido se registre dos veces por errores de interfaz.

Implementar validaciones para evitar enfrentamientos entre equipos incorrectos, duplicación accidental de encuentros y asignaciones inconsistentes.

La modificación de un resultado debe registrar quién la realizó y cuándo.

## 9. MÓDULO DE PLAYOFFS: PRIORIDAD PRINCIPAL

Este módulo debe corregir el problema que apareció durante el campeonato anterior.

El organizador debe poder administrar completamente las fases finales desde su panel, sin necesitar que un administrador técnico cree manualmente las jornadas.

El sistema debe generar las fases eliminatorias a partir de la configuración y de los resultados deportivos disponibles.

### Configuración del playoff

Permitir que el organizador configure:

- Número de equipos clasificados.
- Método de clasificación.
- Cantidad de rondas.
- Eliminatorias a partido único o ida y vuelta.
- Reglas para resolver empates.
- Uso de penales cuando corresponda.
- Fechas y horarios.
- Canchas.
- Reglas de localía.
- Estado de publicación de cada ronda.

Ejemplos de rondas:

- Octavos de final.
- Cuartos de final.
- Semifinales.
- Tercer puesto.
- Final.

Las rondas deben poder adaptarse a diferentes cantidades de participantes, siempre que la configuración elegida sea válida.

No asumir que todos los campeonatos tienen ocho equipos clasificados.

### Flujo de trabajo del organizador

1. El organizador abre su campeonato.
2. Entra al módulo de fases finales.
3. Configura el número de equipos que avanzan.
4. Selecciona si las eliminatorias serán a partido único o ida y vuelta.
5. Configura las reglas de desempate.
6. El sistema muestra una vista previa de los equipos clasificados.
7. El organizador revisa la clasificación.
8. El sistema propone automáticamente los cruces.
9. El organizador revisa y confirma la generación.
10. El sistema crea las rondas, jornadas y partidos correspondientes.
11. El organizador asigna fechas, horarios y canchas.
12. Publica los encuentros cuando estén listos.
13. Registra los resultados de cada partido.
14. El sistema determina qué equipos avanzan.
15. El sistema prepara la siguiente ronda.
16. El organizador revisa y confirma su publicación.

La generación debe realizarse mediante operaciones de negocio independientes de la interfaz gráfica.

### Generación de cruces

Permitir seleccionar entre métodos de emparejamiento compatibles con el reglamento:

- Mejor clasificado contra peor clasificado entre los clasificados, continuando hacia el centro del cuadro.
- Emparejamiento configurable, solo si produce un cuadro completo y sin equipos duplicados.
- Otros métodos válidos para el formato elegido, documentando y probando el orden de siembra y la asignación de cada equipo a una llave.

Si la cantidad de equipos no es potencia de dos, completar el cuadro hasta la siguiente potencia de dos y asignar los descansos (`byes`) a los mejores clasificados, salvo que el reglamento configurado establezca otra regla válida. Mostrar los descansos y sus efectos en la vista previa antes de confirmar la generación. No dejar el orden de siembra ni la asignación de equipos a decisiones implícitas del código.

No asignar cruces hasta que se cumplan las condiciones necesarias de clasificación.

Si los resultados todavía no están completos, mostrar claramente qué partidos faltan y por qué no se puede avanzar.

### Eliminatorias de ida y vuelta

Cuando una eliminatoria tenga dos partidos:

- Relacionar ambos encuentros con una misma eliminatoria.
- Registrar el resultado de ida.
- Registrar el resultado de vuelta.
- Calcular el marcador global.
- Determinar el equipo clasificado cuando las reglas lo permitan.

No considerar que el equipo que gana el partido de vuelta necesariamente gana la eliminatoria.

La clasificación debe calcularse según el resultado global y las reglas configuradas para el campeonato.

### Empates y penales

El organizador debe definir cómo resolver los empates.

Si el reglamento establece penales:
- Registrar los goles de cada equipo en la tanda.
- Distinguir el resultado del partido del resultado de la tanda.
- Identificar al equipo clasificado.
- Mostrar los penales en la interfaz pública.
- Conservar el historial del resultado.

No utilizar la tanda de penales como sustituto del marcador reglamentario.

No implementar reglas de goles de visitante como comportamiento predeterminado. Solo permitirlas si el reglamento las contempla.

### Integridad y seguridad del playoff

La generación de rondas debe ser idempotente: ejecutar dos veces la misma operación no debe duplicar partidos ni jornadas.

Utilizar transacciones de base de datos para las operaciones críticas.

Antes de generar una nueva ronda:
- Verificar que la anterior esté resuelta.
- Verificar que existan los clasificados necesarios.
- Comprobar que no se haya generado previamente.
- Verificar que la configuración no haya cambiado de forma incompatible.

Si el organizador modifica un resultado que afecta una eliminatoria ya generada, no alterar silenciosamente los cruces posteriores.

Detectar la inconsistencia y solicitar una acción explícita al organizador.

Si hay partidos ya disputados en rondas posteriores, impedir una regeneración destructiva automática.

Registrar las acciones importantes en un historial de auditoría.

### Tercer puesto

Permitir habilitar o deshabilitar el partido por el tercer puesto.

Cuando esté habilitado, los equipos eliminados en semifinales podrán ser asignados al encuentro correspondiente.

El partido debe pertenecer al campeonato y a la fase final.

No tratarlo como una final adicional ni incluirlo incorrectamente en los criterios de clasificación general.

### Vista gráfica del playoff

Crear un cuadro eliminatorio visual, responsive y fácil de entender.

Mostrar:
- Rondas.
- Equipos.
- Escudos.
- Marcadores.
- Resultados globales.
- Penales, si existen.
- Estado de los partidos.
- Equipos clasificados.
- Próximo enfrentamiento.

En móviles, utilizar una presentación compacta, navegación entre rondas o desplazamiento horizontal controlado.

El cuadro debe actualizarse a partir de los datos guardados en el sistema.

No mantener una segunda representación manual de los cruces en JavaScript.

## 10. MÓDULO DE CLASIFICACIÓN Y ESTADÍSTICAS

Implementar una tabla de posiciones calculada a partir de los partidos válidos del campeonato.

Mostrar, según el espacio disponible:

- Posición.
- Escudo.
- Equipo.
- Partidos jugados.
- Victorias.
- Empates.
- Derrotas.
- Goles a favor.
- Goles en contra.
- Diferencia de goles.
- Puntos.

En dispositivos móviles, priorizar la información más importante y permitir consultar las estadísticas adicionales sin perder claridad.

Los criterios de desempate deben estar definidos y aplicarse de forma consistente.

No utilizar una clasificación almacenada que quede desactualizada sin un mecanismo de actualización.

Implementar una estrategia de cálculo sencilla y fiable antes de introducir sistemas complejos de caché.

### Estadísticas adicionales

Cuando existan datos suficientes, permitir consultar:

- Goleadores.
- Asistencias, si se registran.
- Tarjetas amarillas.
- Tarjetas rojas.
- Resultados recientes.
- Próximos encuentros.
- Rendimiento de cada equipo.

Las estadísticas deben distinguir entre datos confirmados y datos pendientes de revisión.

## 11. MÓDULO DE JUGADORES Y EVENTOS

Permitir registrar:

- Nombre.
- Apellido.
- Fotografía opcional.
- Dorsal.
- Equipo.
- Estado de participación.
- Goles.
- Tarjetas.
- Otros eventos habilitados.

Los eventos de los partidos deben relacionarse con el encuentro y, cuando corresponda, con el jugador.

No obligar a introducir el minuto de un evento si el reglamento o la organización no lo requieren.

Las modificaciones deben respetar los permisos del usuario y conservar un historial cuando afecten estadísticas oficiales.

## 12. PÁGINA PÚBLICA DEL CAMPEONATO

Crear una página de inicio moderna, deportiva y orientada a los aficionados.

Secciones principales:

- Inicio.
- Próxima jornada.
- Últimos resultados.
- Tabla de posiciones.
- Goleadores.
- Equipos.
- Calendario.
- Playoffs.
- Patrocinadores.
- Contacto.
- Acceso al sistema.

La página inicial debe destacar el próximo partido o los partidos más relevantes.

Las tarjetas de los encuentros deben mostrar:

- Escudos.
- Nombres de los equipos.
- Fecha.
- Hora.
- Cancha.
- Marcador, si el partido ya se disputó.
- Estado del encuentro.

Mostrar las fases finales de manera atractiva, sin sobrecargar la página.

La navegación debe ser sencilla y funcionar bien sin iniciar sesión.

## 13. PANEL DEL ORGANIZADOR

Diseñar un panel administrativo propio, independiente del Django Admin.

El panel debe permitir trabajar de manera visual y rápida.

Secciones recomendadas:

- Resumen.
- Campeonatos.
- Equipos.
- Jugadores.
- Jornadas.
- Partidos.
- Resultados.
- Clasificación.
- Playoffs.
- Pagos, si corresponde.
- Notificaciones.
- Configuración.

El resumen debe mostrar información relevante, como:

- Próximos partidos.
- Resultados pendientes.
- Jornadas sin publicar.
- Equipos inscritos.
- Estado del campeonato.
- Alertas de configuración.
- Estado de las fases finales.

Incluir accesos directos a las tareas frecuentes.

No convertir el panel en una copia innecesariamente compleja del Django Admin.

## 14. SISTEMA DE NOTIFICACIONES

Implementar notificaciones internas para eventos relevantes:

- Publicación de jornadas.
- Cambios de horarios.
- Cambios de cancha.
- Resultados publicados.
- Inicio de fases finales.
- Clasificación de equipos.
- Cambios importantes del campeonato.

Preparar la integración con Web Push cuando se encuentre configurada.

El funcionamiento principal de la aplicación no debe depender de que las notificaciones push estén disponibles.

Los errores deben mostrarse mediante mensajes claros, con colores e iconos apropiados.

## 15. IDENTIDAD VISUAL Y CONFIGURACIÓN POR CAMPEONATO

Cada campeonato debe poder configurar:

- Nombre público.
- Logotipo.
- Colores principales.
- Imagen de portada.
- Información de contacto.
- Redes sociales.
- Patrocinadores.

Mantener una identidad visual coherente entre las páginas públicas y el panel de gestión.

Evitar que un cambio de color requiera modificar múltiples plantillas.

Usar variables CSS y componentes reutilizables de Django.

## 16. COMPONENTES REUTILIZABLES DE FRONTEND

Crear componentes mediante includes de Django y convenciones consistentes.

Ejemplos:

- Barra de navegación.
- Menú móvil.
- Pie de página.
- Tarjeta de equipo.
- Tarjeta de partido.
- Marcador.
- Insignia de estado.
- Mensajes de notificación.
- Confirmación de acciones.
- Tabla de clasificación.
- Tarjeta de jugador.
- Tarjeta de estadísticas.
- Cuadro de playoffs.
- Formularios.
- Paginación.
- Indicador de carga.

Mantener los estilos organizados.

Utilizar Bootstrap para cuadrículas, formularios, botones, modales, navegación y utilidades.

Crear CSS propio solo para necesidades visuales específicas del proyecto.

Evitar archivos CSS monolíticos y scripts JavaScript que mezclen todas las funcionalidades.

## 17. SEGURIDAD Y VALIDACIONES

Implementar:

- Protección CSRF.
- Validación de formularios en el servidor.
- Control de permisos.
- Consultas restringidas al campeonato autorizado.
- Protección contra modificaciones no autorizadas.
- Manejo correcto de errores.
- Validación de archivos subidos.
- Uso adecuado de transacciones.
- Prevención de duplicados.
- Registro de operaciones sensibles.
- Configuración segura para producción.

No confiar exclusivamente en validaciones JavaScript.

Los resultados oficiales y las clasificaciones deben calcularse y validarse en el backend.

## 18. RENDIMIENTO Y ESCALABILIDAD

El sistema debe funcionar inicialmente con SQLite.

Diseñar los modelos y consultas para evitar duplicaciones y facilitar futuras ampliaciones.

Aplicar:
- Relaciones de base de datos correctas.
- Restricciones de integridad.
- Índices donde estén justificados.
- `select_related()` y `prefetch_related()` cuando corresponda.
- Paginación para listados extensos.
- Consultas eficientes.
- Separación entre datos públicos y administrativos.
- Servicios de dominio reutilizables.

No introducir microservicios, colas de tareas o infraestructura adicional sin una necesidad demostrable.

Evitar consultas repetitivas por cada elemento de una lista.

La arquitectura debe permitir evolucionar sin tener que reconstruir todos los módulos.

## 19. PRUEBAS AUTOMATIZADAS

Crear pruebas con Django TestCase para los flujos críticos.

Priorizar:

- Creación de campeonatos.
- Asignación de permisos.
- Separación de datos entre campeonatos.
- Creación de jornadas.
- Generación de partidos.
- Cálculo de posiciones.
- Cálculo de resultados globales.
- Clasificación de equipos.
- Resolución mediante penales.
- Generación de cuadros eliminatorios.
- Prevención de jornadas duplicadas.
- Prevención de partidos duplicados.
- Cambios de resultados.
- Integridad de las rondas posteriores.
- Acceso desde usuarios con diferentes roles.

Incluir pruebas específicas para el problema histórico del playoff.

Simular un campeonato completo desde la fase regular hasta la final.

Verificar que el organizador pueda administrar las fases finales sin acceso al administrador técnico.

## 20. DESPLIEGUE

Mantener compatibilidad con PythonAnywhere y SQLite.

Separar la configuración de desarrollo y producción.

Utilizar variables de entorno para secretos y parámetros sensibles.

No incluir claves secretas en el repositorio.

Documentar:
- Instalación.
- Migraciones.
- Creación de superusuario.
- Configuración de archivos estáticos.
- Configuración de archivos multimedia.
- Variables de entorno.
- Despliegue.
- Copias de seguridad de SQLite.
- Actualización de versiones.

No asumir que los archivos estáticos y multimedia se gestionan de la misma manera.

La aplicación debe poder actualizarse sin perder los datos existentes.

## 21. METODOLOGÍA DE DESARROLLO

Trabajar por fases y evitar cambios masivos sin verificación.

### Fase 1. Auditoría
Inspeccionar el código existente.

Identificar:
- Aplicaciones Django.
- Modelos.
- Relaciones.
- Vistas.
- URLs.
- Plantillas.
- CSS.
- JavaScript.
- Dependencias.
- Migraciones.
- Funcionalidades existentes.
- Problemas del playoff.

Entregar un diagnóstico y un plan de implementación.

Mantén el informe conciso y basado en evidencia: para cada conclusión importante, indica los archivos, modelos o funciones revisados y distingue los hechos observados de las recomendaciones. Si un aspecto no puede comprobarse con el código disponible, señálalo como pendiente de verificación en lugar de asumir una respuesta.

No modificar archivos todavía.

### Fase 2. Arquitectura
Definir la arquitectura objetivo.

Revisar las relaciones entre campeonatos, equipos, jornadas, partidos, resultados y playoffs.

Proponer los cambios de modelos y migraciones necesarios.

Identificar qué funcionalidades pueden reutilizarse.

Evitar reconstruir innecesariamente las partes que ya funcionan.

### Fase 3. Diseño visual
Definir:
- Paleta de colores.
- Tipografía.
- Componentes.
- Estructura de navegación.
- Plantilla base.
- Diseño público.
- Panel del organizador.
- Adaptación móvil.

Bootstrap 5 es el sistema objetivo para los nuevos componentes, conforme a las tecnologías obligatorias. Primero audita las dependencias y plantillas existentes. Si se confirma el uso de Tailwind CSS, propón y ejecuta su sustitución de forma gradual, verificando cada área y evitando mantener ambos sistemas como solución permanente. Si Tailwind no está presente, no realices una migración ficticia ni reescribas estilos existentes sin una razón técnica concreta.

### Fase 4. Módulos fundamentales
Implementar primero:
- Core.
- Usuarios y permisos.
- Campeonatos.
- Equipos.
- Jugadores.
- Jornadas.
- Partidos.

### Fase 5. Playoffs
Desarrollar el módulo de fases finales como prioridad funcional.

Implementar los servicios de generación de rondas, cálculo de clasificados, validaciones y prevención de duplicados.

Crear pruebas automatizadas antes de dar por terminado el módulo.

### Fase 6. Clasificación y estadísticas
Integrar las estadísticas con los resultados oficiales.

### Fase 7. Frontend público
Construir la página pública y sus componentes responsive.

### Fase 8. Panel del organizador
Implementar la gestión administrativa con Bootstrap 5.

### Fase 9. Notificaciones y funciones complementarias
Incorporar las funciones adicionales después de estabilizar el núcleo.

### Fase 10. Validación y despliegue
Ejecutar pruebas, revisar permisos, comprobar las vistas móviles y documentar el despliegue.

## 22. REGLAS OBLIGATORIAS PARA EL AGENTE DE PROGRAMACIÓN

1. Antes de escribir código, inspecciona el proyecto existente.
2. No inventes modelos ni relaciones sin revisar los actuales.
3. No elimines datos ni funcionalidades sin autorización.
4. No ejecutes migraciones destructivas sin explicar sus consecuencias.
5. No cambies la base de datos a PostgreSQL.
6. No añadas Tailwind CSS ni lo uses en componentes nuevos; si ya existe en el proyecto, sigue la migración gradual descrita en la Fase 3.
7. No instales dependencias sin justificar su necesidad.
8. No reconstruyas toda la aplicación en una sola operación.
9. No dupliques lógica de negocio en las vistas y el frontend.
10. Para las garantías de generación, idempotencia y protección de resultados o cruces existentes, aplica los requisitos detallados en la sección 9 (Playoffs).
11. No marques una funcionalidad como terminada si solo tiene una interfaz visual.
12. Ejecuta las pruebas correspondientes a cada módulo.
13. Mantén un registro de los archivos modificados y las decisiones técnicas.
14. Documenta las nuevas funcionalidades y los cambios de arquitectura.
15. Utiliza Bootstrap 5 y plantillas Django para mantener el frontend ligero.
16. Conserva la compatibilidad con el despliegue previsto en PythonAnywhere.
17. Prioriza la facilidad de uso del organizador.
18. Entrega código funcional, no únicamente ejemplos o pseudocódigo.

## 23. PRIMERA TAREA

Comienza exclusivamente por la FASE 1: AUDITORÍA.

Inspecciona el repositorio actual y entrega:

1. Resumen de la arquitectura existente.
2. Inventario de aplicaciones y modelos.
3. Relaciones principales entre los modelos.
4. Descripción del flujo actual para crear jornadas y partidos.
5. Diagnóstico del sistema de playoffs.
6. Identificación de los problemas que podrían causar duplicaciones o clasificaciones incorrectas.
7. Inventario de plantillas y tecnologías frontend.
8. Verificación del uso de Tailwind y, solo si está presente, plan de migración a Bootstrap 5.
9. Propuesta de arquitectura modular.
10. Plan de migraciones y conservación de datos.
11. Lista priorizada de mejoras.
12. Propuesta de pruebas automatizadas.

Para el punto 8, comprueba primero si Tailwind está instalado o se utiliza en las plantillas. Si no se encuentra, indícalo y describe únicamente cómo se aplicará Bootstrap 5 a componentes nuevos o que deban cambiarse; no propongas una migración inexistente.

Presenta los resultados en secciones breves y priorizadas. En el inventario, incluye solo los modelos y relaciones relevantes para los flujos principales, con referencias a los archivos inspeccionados. Separa hechos comprobados, riesgos y recomendaciones; no infieras comportamientos que no estén respaldados por el código.

No modifiques archivos durante esta primera fase.

Al terminar, espera la aprobación antes de comenzar a implementar los cambios.