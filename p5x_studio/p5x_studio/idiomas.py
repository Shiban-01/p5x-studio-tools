"""Idiomas de P5X Studio: espanol (por defecto) e ingles.

Un solo sitio para todo el texto que ve el usuario. Las claves van planas pero agrupadas por zona
con un prefijo, para saber de un vistazo de donde sale cada cadena:

    cab_  cabecera            est_  panel de estado       pie_  barra de accion
    lista_/traje_  eleccion   cat_  categorias            opt_/base_  opciones
    msg_/log_/det_  mensajes y registro de la pestana de extraccion
    her_  pestana de herramientas (toda)
    dep_/su_/ind_/un_/gr_/fb_/cl_/ct_/tr_  modulos de apoyo
    ex_   extractor (progreso, avisos y los ficheros LEEME/README que escribe)

Uso:
    from .idiomas import t
    texto = t("est_comprobar")
    texto = t("det_ficha", etiqueta, n, tipos)     # con %s/%d
    idiomas.activar("en")

Para que la interfaz cambie de idioma AL MOMENTO, sin reconstruirla, los widgets se apuntan en un
registro: al crear cada widget se llama a `registrar(funcion)` con una funcion que le vuelve a
poner el texto. `activar()` recorre el registro y las ejecuta todas.
"""
from __future__ import annotations

IDIOMAS = {"es": "Español", "en": "English"}
POR_DEFECTO = "es"

_ACTIVO = {"v": POR_DEFECTO}

# --------------------------------------------------------------------------- registro de widgets
_REGISTRO: list = []


def registrar(funcion) -> None:
    """Apunta una funcion que reaplica el texto de un widget. La llama una vez ya."""
    _REGISTRO.append(funcion)
    try:
        funcion()
    except Exception:
        pass


def refrescar() -> None:
    """Vuelve a aplicar todos los textos registrados (tras cambiar de idioma)."""
    for funcion in list(_REGISTRO):
        try:
            funcion()
        except Exception:
            pass


def olvidar_registro() -> None:
    _REGISTRO.clear()


def idioma_actual() -> str:
    return _ACTIVO["v"]


def activar(idioma: str) -> None:
    """Fija el idioma activo y refresca la interfaz ya construida."""
    _ACTIVO["v"] = idioma if idioma in IDIOMAS else POR_DEFECTO
    refrescar()


def _textos(clave: str):
    es = ES.get(clave)
    en = EN.get(clave)
    return es, en


def t(clave: str, *args, **kwargs) -> str:
    """Texto de `clave` en el idioma activo, con sustituciones opcionales."""
    tabla = EN if _ACTIVO["v"] == "en" else ES
    texto = tabla.get(clave)
    if texto is None:
        # red de seguridad: si falta la traduccion, se usa el espanol y, si tampoco, la clave
        texto = ES.get(clave, clave)
    if kwargs:
        try:
            return texto.format(**kwargs)
        except Exception:
            return texto
    if args:
        try:
            return texto % args
        except Exception:
            return texto
    return texto


def claves_faltantes() -> dict:
    """Para verificacion: claves que faltan en cada idioma respecto al otro."""
    return {"faltan_en_en": sorted(set(ES) - set(EN)),
            "faltan_en_es": sorted(set(EN) - set(ES))}


# =========================================================================== ESPANOL
ES = {
    # ---------------------------------------------------------------- interfaz nueva (web)
    "web_brand_sub": "Tools",
    "web_nav_bundles": "Bundles",
    "web_nav_inspector": "Inspector",
    "web_nav_resources": "Recursos",
    "web_nav_textures": "Texturas",
    "web_nav_media": "Vídeo y audio",
    "web_foot_index": "Índice: %s bundles",
    "web_loading": "Cargando…",
    "web_error": "Error: %s",
    "web_soon_title": "En construcción",
    "web_soon_body": "Esta pantalla todavía no está cableada al motor. No se muestran datos inventados.",
    "web_note": "Los datos salen de tu copia del juego. Nada se inventa: lo que no se sabe, se deja en blanco.",

    # --- explorador
    "web_explore_title": "Explora los bundles del juego",
    "web_explore_sub": "Busca por nombre, filtra por tipo y lee lo que llevan dentro sin abrir nada.",
    "web_search_placeholder": "part_l_normal, shared_, scn_hougewai…",
    "web_chip_all": "Todo",
    "web_new": "Nuevo",
    "web_new_only": "Solo nuevos",
    "web_new_mark": "Marcar como vistos",
    "web_new_done": "%s bundles marcados como vistos",
    "web_results": "Resultados",
    "web_shown": "%s de %s mostrados",
    "web_empty": "Nada coincide con esa búsqueda.",
    "web_source_disk": "Leído de la carpeta del juego, sin índice.",
    "web_unit_mesh": "malla",
    "web_unit_mesh_pl": "mallas",
    "web_unit_tex": "tex",
    "web_d_meshes": "Mallas",
    "web_d_textures": "Texturas",
    "web_d_size": "Tamaño",
    "web_d_type": "Tipo",
    "web_d_contents": "Contenido",
    "web_d_open": "Abrir con el motor",
    "web_d_extract": "Extraer este bundle",
    "web_d_reveal": "Ver en la carpeta",
    "web_d_close": "Cerrar",
    "web_d_actors": "Actores",
    "web_d_costumes": "Trajes",
    "web_d_role": "Papel",
    "web_d_what": "Qué es",
    "web_none": "—",

    # --- inspector
    "web_insp_title": "Inspector de un bundle",
    "web_insp_sub": "Abre un bundle con el motor y mira qué recursos lleva dentro, por nombre y tipo.",
    "web_insp_path": "Ruta del bundle",
    "web_insp_ph": "110/shared_....bundle",
    "web_insp_open": "Abrir con el motor",
    "web_insp_choose": "Elegir fichero…",
    "web_col_name": "Nombre",
    "web_col_type": "Tipo",
    "web_col_container": "Contenedor",
    "web_col_pathid": "PathID",
    "web_col_size": "Tamaño",
    "web_insp_export": "Exportar seleccionados",
    "web_insp_export_all": "Exportar todo (mallas + texturas)",
    "web_insp_empty": "Abre un bundle para ver qué lleva dentro.",
    "web_insp_working": "Abriendo…",
    "web_insp_n": "%s recursos",

    # --- buscador
    "web_res_title": "Buscador de recursos",
    "web_res_sub": "Busca una malla o textura por su nombre en TODO el juego.",
    "web_res_ph": "nombre de malla o textura…",
    "web_res_build": "Construir índice",
    "web_res_rebuild": "Reconstruir",
    "web_res_cancel": "Cancelar",
    "web_res_none": "Todavía no hay índice del buscador.",
    "web_res_none_body": "Construirlo abre cada bundle con el motor; con los 16.535 tarda unos 29 minutos. Se puede cancelar, y lo hecho no se guarda a medias.",
    "web_res_building": "Construyendo índice: %s / %s",
    "web_res_ready": "Índice listo: %s recursos en %s bundles.",
    "web_res_parcial": "Índice PARCIAL: cubre %s de %s bundles (%s recursos). Vuelve a construirlo para que busque en todo el juego.",
    "web_res_cancelled": "Cancelado. No se guardó nada.",
    "web_res_empty": "Nada coincide.",
    "web_col_bundle": "Bundle",

    # --- texturas
    "web_tex_title": "Visor de texturas",
    "web_tex_sub": "Mira las imágenes que salgan de una extracción, sin salir de la aplicación.",
    "web_tex_bundle": "Bundle del que extraer",
    "web_tex_export": "Extraer texturas",
    "web_tex_folder": "Carpeta con imágenes",
    "web_tex_choose": "Elegir carpeta…",
    "web_tex_scan": "Buscar imágenes",
    "web_tex_none": "No hay imágenes en esa carpeta. Extrae texturas de un bundle o elige otra carpeta.",
    "web_tex_n": "%s imágenes",
    "web_tex_working": "Extrayendo…",

    # --- video y audio
    "web_media_title": "Vídeo y audio",
    "web_media_sub": "Los vídeos y la música del cliente. Al extraer un vídeo se conservan TODAS sus pistas de audio.",
    "web_media_videos": "Vídeos",
    "web_media_audios": "Audio",
    "web_media_list": "Listar",
    "web_media_none": "No encuentro la carpeta de medios del juego.",
    "web_media_n": "%s ficheros",
    "web_media_extract_video": "Extraer MP4",
    "web_media_extract_audio": "Extraer WAV",
    "web_media_open_out": "Abrir carpeta de salida",
    "web_media_working": "Extrayendo…",
    "web_media_done": "Listo: %s",
    "web_deps_btn": "Dependencias",
    "web_nav_settings": "Ajustes",
    "web_settings_title": "Ajustes",
    "web_settings_sub": "Personaliza el tema, las rutas del juego y las opciones de la herramienta.",
    "web_theme_label": "Tema",
    "web_theme_desc": "Elige la paleta de colores de la interfaz.",
    "web_settings_game_path": "Instalación del juego",
    "web_settings_game_desc": "La carpeta del juego P5X que se está analizando. Si la detección automática falla o tienes varias instalaciones, elige la correcta.",
    "web_settings_choose_game": "Elegir carpeta…",
    "web_settings_detect": "Auto-detectar",
    "web_settings_game_ok": "Juego detectado — Steam (Global)",
    "web_settings_tex_path": "Carpeta de texturas",
    "web_settings_tex_desc": "Dónde se guardan las texturas de retratos extraídas.",
    "web_settings_choose_tex": "Elegir carpeta…",
    "web_settings_tex_ok": "3,258 sprites encontrados",
    "web_settings_out_path": "Carpeta de salida",
    "web_settings_out_desc": "Dónde se guardan los bust-ups y texturas exportados.",
    "web_settings_choose_out": "Elegir carpeta…",
    "web_settings_about": "Información",
    "web_settings_version": "Versión",
    "web_settings_bundles": "Bundles indexados",
    "web_settings_bustups": "Bust-ups disponibles",
    "web_settings_shaders": "Perfiles de shader",
    "web_settings_thumbs": "Miniaturas",
    "web_deps_title": "Dependencias",
    "web_deps_peso": "Hacen falta estas herramientas (~%s MB en total). Se bajan solas a la carpeta tools/.",
    "web_deps_bajar": "Descargar dependencias",
    "web_deps_solo_ver": "Esta consola es solo para mirar: no se puede escribir en ella.",
    "web_deps_cerrar": "Cerrar",
    "web_deps_uv": "uv (monta el entorno de wannacri)",
    "web_deps_motor": "Motor (lee los bundles)",
    "web_deps_wannacri": "wannacri (saca el vídeo de los .usm)",
    "web_deps_vgmstream": "vgmstream (lee el audio de los .acb)",
    "web_deps_ffmpeg": "ffmpeg (monta el MP4)",
    "web_deps_si": "instalado",
    "web_deps_no": "falta",
    "web_deps_fuera": "fuera de la carpeta",
    "web_deps_fuera_ayuda": "La app la usa desde fuera de la carpeta (no viaja con ella): el botón se baja la suya.",
    "web_deps_listo": "Listo: %s herramientas.",
    "web_deps_fallo": "Se bajó el resto, pero algo falló:",
    "dep_motor_ajeno": "Tienes una copia del motor fuera de la herramienta (%s); me bajo la mía para que la carpeta sirva en otro equipo.",
    "web_media_legend": "Pistas de audio etiquetadas: jpn (japonés), chi (chino) y und (efectos, sin voz). «sin_dato» significa que no se puede saber sin decodificar; es la verdad, no un error.",
    "web_audio_audio": "con audio",
    "web_audio_silencio": "silencio",
    "web_audio_mudo": "sin audio",
    "web_audio_sin_dato": "sin_dato",

    # ---------------------------------------------------------------- comun
    "comun_todo": "Todo",
    "comun_buscar": "Buscar",
    "comun_comprobando": "comprobando...",
    "comun_idioma": "Idioma:",
    "comun_idioma_nombre": "Español",

    # ---------------------------------------------------------------- cabecera
    "cab_lema": "Extrae los modelos del juego y los deja ordenados, con sus texturas "
                "y vistas previas.",

    # ---------------------------------------------------------------- pestanas
    "tab_extraccion": "  Extraccion  ",
    "tab_herramientas": "  Herramientas  ",

    # ---------------------------------------------------------------- panel de estado
    "est_titulo": "Estado",
    "est_comprobar": "Comprobar de nuevo",
    "est_juego": "Instalacion del juego",
    "est_librerias": "Librerias necesarias",
    "est_indice": "Indice de modelos",
    "est_esqueleto": "Esqueleto (Unity)",
    "est_encontrado": "encontrado: %s",
    "est_no_encontrado": "no encontrado: usa el boton para indicar la carpeta",
    "est_listas": "listas",
    "est_personajes": "%d personajes",
    "est_unity_ok": "listo: editor, licencia y proyecto",
    "est_esqueleto_bundles": "listo: huesos y pesos desde los bundles del juego",
    "est_esqueleto_bundles_unity": "listo desde los bundles (Unity tambien disponible, de respaldo)",
    "est_unity_sin_editor": "sin editor de Unity: no habra esqueleto ni pesos de piel",
    "est_unity_sin_licencia": "falta la licencia: pulsa «Iniciar sesion en Unity»",
    "est_unity_sin_proyecto": "falta el proyecto de Unity decompilado del juego",
    "btn_elegir_carpeta": "Elegir carpeta del juego",
    "btn_actualizar_librerias": "Actualizar librerias",
    "btn_sesion_unity": "Iniciar sesion en Unity",

    # ---------------------------------------------------------------- barra de accion
    "pie_extraer": "Extraer modelo",
    "pie_abrir": "Abrir la carpeta del modelo",
    "pie_listo": "Listo para empezar.",
    "pie_extraido": "Modelo extraido.",
    "pie_error": "No se pudo completar.",

    # ---------------------------------------------------------------- eleccion de personaje
    "lista_paso1": "1. Busca el personaje",
    "lista_mostrar": "Mostrar:",
    "lista_cuenta": "%d en la lista",
    "traje_label": "Traje:",
    "traje_cuenta": "%d trajes: elige uno",
    "traje_valor": "%s  (%d mallas, %d texturas)",

    # ---------------------------------------------------------------- categorias
    "cat_personaje": "Personajes",
    "cat_objeto": "Objetos",
    "cat_escenario": "Escenarios",
    "cat_efecto": "Efectos",
    "cat_camara": "Camaras",
    "cat_valor": "%s (%d)",

    # ---------------------------------------------------------------- opciones
    "opt_titulo": "2. Elige que extraer",
    "opt_mallas": "Modelos (geometria)",
    "opt_texturas": "Texturas",
    "opt_materiales": "Materiales",
    "opt_esqueleto": "Esqueleto y expresiones",
    "opt_previas": "Vistas previas",
    "opt_fbx": "FBX con todo unido",
    "opt_armas": "Incluir armas del personaje",
    "opt_paso3": "3. Extrae",
    "opt_pie": "Pulsa el boton «Extraer modelo» que esta abajo del todo.",
    "base_titulo": "4. Modelo base (para skins)",
    "base_vacio": "Elige un personaje de la lista.",
    "base_fijar": "Fijar como base",
    "base_quitar": "Quitar",

    # ---------------------------------------------------------------- registro
    "log_titulo": "Lo que va pasando",

    # ---------------------------------------------------------------- mensajes de la ventana
    "msg_ocupado": "Ya hay una tarea en marcha. Espera a que acabe.",
    "msg_no_completar": "No se pudo completar.",
    "msg_no_completar_detalle": "No se pudo completar: %s",
    "msg_extraido_titulo": "Modelo extraido correctamente.\n\nSe ha guardado en:\n%s",
    "msg_listo_en": "Listo. El modelo esta en: %s",
    "log_comprobando_instalacion": "Comprobando la instalacion...",
    "log_juego_encontrado": "  Juego encontrado en %s",
    "log_juego_no": "  No encuentro el juego. Lo puedes indicar a mano.",
    "log_preparando_librerias": "Preparando las librerias...",
    "log_leyendo_indice": "Leyendo el indice de modelos...",
    "log_todo_listo": "Todo listo. Ya puedes buscar un personaje.",
    "estado_elige_extraer": "Elige un personaje y pulsa Extraer.",
    "log_aviso": "Aviso: %s",
    "estado_revisa_avisos": "Revisa los avisos de arriba.",
    "msg_unity_ya": "Unity ya tiene licencia guardada. La extraccion del esqueleto "
                    "y de los pesos de piel funcionara sin pedirte nada.",
    "msg_unity_sin_editor": "No encuentro el editor de Unity en el equipo.\n\n"
                            "Hace falta para sacar el esqueleto y los pesos, que es lo unico "
                            "que no se puede obtener de los bundles. Sin el, la herramienta "
                            "te da geometria, texturas, materiales y el FBX unido, pero no "
                            "el rig.",
    "dlg_carpeta_juego_titulo": "Elige la carpeta del juego (la que contiene Client)",
    "msg_carpeta_no_valida": "Esa carpeta no es la del juego.\n\n"
                             "Elige la carpeta que contiene «Client\\OuterPackage\\Bundles\\Windows», "
                             "o directamente esa misma carpeta de bundles.\n\n"
                             "No la he guardado. No hace falta descompilar ni desofuscar nada: el motor "
                             "lee los bundles tal cual, con su nombre tal como viene.",
    "log_carpeta_fijada": "Carpeta del juego fijada en: %s",
    "log_bundles_encontrados": "  bundles encontrados: %d",
    "msg_carpeta_guardada": "Carpeta del juego guardada.\n\n%s\n\nEncontrados %d bundles. "
                            "Se recordara la proxima vez que abras la herramienta.",
    "log_buscando_versiones": "Buscando versiones nuevas...",
    "log_todo_aldia": "Todo esta al dia.",
    "msg_hay_nuevas": "Hay versiones nuevas de: %s\n\n¿Actualizarlas ahora?",
    "log_librerias_actualizadas": "Librerias actualizadas.",
    "log_no_actualizar": "No se pudo actualizar: %s",

    # ---------------------------------------------------------------- detalle de la lista
    "det_ficha": "%s: %d ficheros (%s)",
    "det_trae": "   trae: %s",
    "det_skin": "   OJO: es una skin. Su cara vive en el modelo base, que son otros "
                "bundles; lo que salga aqui no tendra cara.",
    "det_otros": "   (%d ficheros mas que NO son del modelo: timelines, escenarios o "
                 "efectos; no se extraen)",
    "det_trajes": "   trajes: %s",
    "det_traje_aviso": "   se extraera el traje elegido en el desplegable «Traje».",
    "det_traje_elegido": "   traje elegido: %s (%d ficheros)",
    "det_base_declarado": "   modelo base declarado: %s",
    "det_base_posible": "   posible modelo base (pulsa «Fijar como base»): %s -> %s",
    "det_base_fijado": "   base %s declarado para %s.",
    "det_base_quitado": "   base quitado a %s.",

    # ---------------------------------------------------------------- modelo base
    "base_msg_no_personaje": "No es un personaje: no necesita modelo base.",
    "base_msg_declarado": "Base declarado: %s (%s).",
    "base_msg_propia": "Este personaje ya trae cara propia: no necesita base.",
    "base_msg_posible": "Skin sin base declarado. Posible base: %s.",
    "base_msg_sin_pista": "Skin sin base declarado y sin pista clara: busca el base a mano.",
    "base_err_corto": "Escribe al menos dos letras del nombre del base.",
    "base_err_buscar": "No pude buscar: %s",
    "base_marca_cara": "CARA",
    "base_lista_vacia": "  (nada con cara; prueba otro trozo del nombre)",
    "base_err_sin_personaje": "Primero elige el personaje de la lista.",
    "base_err_sin_seleccion": "Elige antes un modelo base de la lista de abajo.",
    "base_err_faltan": "Hacen falta el personaje y su modelo base.",
    "base_err_propio": "Un modelo no puede ser su propio base.",
    "base_motivo": "aparece en: %s",

    # ---------------------------------------------------------------- extraccion
    "extraer_err_sin_personaje": "Primero elige un personaje de la lista.",
    "extraer_err_sin_indice": "Todavia estoy preparando el indice. Un momento.",
    "extraer_pregunta_unity": "El esqueleto y los pesos de piel necesitan Unity en modo lote, "
                              "y ahora mismo no se puede:\n\n%s.\n\n"
                              "El resto del modelo (geometria, texturas, materiales y el FBX "
                              "unido) si se puede extraer sin Unity, pero el modelo no saldra "
                              "riggeado.\n\n¿Extraer el modelo sin esqueleto?",

    # ---------------------------------------------------------------- HERRAMIENTAS
    "her_titulo": "Herramientas del juego",
    "her_lema": "Explora los 16.535 bundles, abre uno con el motor, busca cualquier "
                "recurso por su nombre y saca videos y musica del cliente.",
    "her_tab_explorador": "  Explorador de bundles  ",
    "her_tab_inspector": "  Inspector de un bundle  ",
    "her_tab_buscador": "  Buscador de recursos  ",
    "her_tab_texturas": "  Visor de texturas  ",
    "her_tab_media": "  Video y audio  ",

    "her_tipo": "Tipo:",
    "her_actor": "Actor:",
    "her_traje": "Traje:",
    "her_min_mb": "Min. MB:",
    "her_filtrar": "Filtrar",
    "her_bundles_de": "%d bundles (de %d)",
    "her_solo_4000": "  — solo se muestran los 4000 primeros",
    "her_col_bundle": "Bundle",
    "her_col_tipo": "Tipo",
    "her_col_papel": "Papel",
    "her_col_mb": "MB",
    "her_col_mallas": "Mallas",
    "her_col_texturas": "Texturas",
    "her_col_contenido": "Contenido",
    "her_ver_dentro": "Ver dentro",
    "her_exportar_mesh_tex": "Exportar mallas + texturas",
    "her_det_tipo_papel": "tipo: %s   papel: %s",
    "her_det_que_es": "que es: %s",
    "her_det_tamano": "tamano: %.2f MB",
    "her_det_actores": "actores: %s",
    "her_det_trajes": "trajes: %s",
    "her_det_quien": "quien: %s",
    "her_det_contenido": "contenido: %s",
    "her_det_mallas": "mallas (%d): %s",
    "her_det_texturas": "texturas (%d): %s",

    "her_bundle": "Bundle:",
    "her_elegir_fichero": "Elegir fichero...",
    "her_abrir_motor": "Abrir con el motor",
    "her_col_nombre": "Nombre",
    "her_col_tipo2": "Tipo",
    "her_col_contenedor": "Contenedor",
    "her_col_pathid": "PathID",
    "her_col_tamano": "Tamano",
    "her_exportar": "Exportar:",
    "her_mallas": "Mallas",
    "her_texturas": "Texturas",
    "her_mallas_texturas": "Mallas + texturas",
    "her_todo_posible": "Todo lo que se pueda",
    "her_msg_ruta": "Escribe o elige la ruta de un bundle.",
    "her_abriendo": "Abriendo con el motor...",
    "her_recursos_dentro": "   %d recursos dentro de %s",
    "her_n_recursos": "%d recursos",
    "dlg_bundle_titulo": "Elige un bundle del juego",
    "dlg_bundle_unity": "Bundles de Unity",
    "dlg_bundle_todos": "Todos",

    "her_recurso": "Recurso:",
    "her_col_recurso": "Recurso",
    "her_col_tipo3": "Tipo",
    "her_col_bundle": "Bundle",
    "her_coincidencias": "%d coincidencias (indice de %d recursos)",
    "her_msg_dos_letras": "Escribe al menos dos letras del nombre.",
    "her_log_buscador": "Buscador: «%s» -> %d coincidencias",
    "her_ver_bundle": "Ver el bundle",
    "her_exportar_bundle": "Exportar el bundle",

    "her_carpeta": "Carpeta:",
    "her_elegir_carpeta": "Elegir carpeta...",
    "her_listar_imagenes": "Listar imagenes",
    "dlg_carpeta_img_titulo": "Carpeta con imagenes extraidas",
    "her_elige_imagen": "Elige una imagen de la lista.",
    "her_n_imagenes": "%d imagenes en la carpeta.",
    "her_sin_imagenes": "No hay imagenes aqui.\nExporta algo y vuelve a listar.",
    "her_sin_pillow": "No hay Pillow: %s",
    "her_err_imagen": "No se pudo abrir esta imagen:\n%s",

    "her_herr_externas": "Herramientas externas",
    "her_herr_ok": "✓ %s",
    "her_herr_no": "✗ falta %s",
    "her_wannacri": "wannacri (.usm -> video)",
    "her_vgmstream": "vgmstream (.awb -> wav)",
    "her_ffmpeg": "ffmpeg (empaquetar video)",
    "her_motor": "motor AssetStudio (bundles)",
    "her_comprobar_herr": "Comprobar herramientas",
    "her_mostrar": "Mostrar:",
    "her_videos": "Videos (.usm)",
    "her_audios": "Audio (.awb)",
    "her_listar": "Listar",
    "her_extraer_elegido": "Extraer el elegido",
    "her_media_ayuda": "MP4 con sonido; pistas etiquetadas. Audio suelto: WAV.",
    "her_extraer_mp4": "Extraer a MP4",
    "her_extraer_wav": "Extraer a WAV",
    "her_abrir_salida": "Abrir la carpeta de salida",
    "her_no_carpeta_media": "No encuentro la carpeta de videos y audio del cliente.",
    "her_log_no_media": "Video y audio: no encuentro Client/OuterPackage/Media/Windows.",
    "her_ficheros_en": "%d ficheros en %s",
    "her_media_resumen": "%d con audio · %d silencio · %d sin audio",
    "her_video_con_audio": "♪ con audio",
    "her_video_sin_audio": "— sin audio",
    "her_video_silencio": "⚠ silencio",
    "her_video_sin_dato": "? sin dato",
    "her_leyenda_audio": "Distintivo de audio (antes de extraer): ♪ con audio  ·  — sin audio  ·  "
                         "⚠ la pista existe pero suena a silencio.",
    "her_msg_elige_fichero": "Elige primero un fichero de la lista.",
    "her_log_extrayendo_video": "Extrayendo video: %s",
    "her_estado_video_listo": "Video listo: %s",
    "her_log_video_extraido": "Video extraido: %s",
    "her_log_extrayendo_audio": "Extrayendo audio: %s",
    "her_estado_audio_listo": "%d pista(s) de audio listas",
    "her_exportando": "Exportando %s...",
    "her_log_exportando": "Exportando %s -> %s",
    "her_log_n_ficheros": "   %d ficheros en la carpeta de salida",
    "her_estado_exportado": "Exportado: %s",
    "her_log_export_terminada": "Exportacion terminada en: %s",
    "her_log_comprobando_herr": "Comprobando herramientas externas...",
    "her_disponible": "disponible: %s",
    "her_no_disponible": "NO disponible",
    "her_err_no_completar": "No se pudo completar: %s",
    "her_motor_falta": "Falta el motor de extraccion (AssetStudioModCLI). Pulsa «Actualizar "
                       "librerias» en la pestana de extraccion.",
    "her_err_bundle": "No encuentro el bundle en el juego: %s",
    "her_log_abriendo": "   abriendo %s ...",
    "her_err_sin_lista": "El motor no devolvio la lista de assets.\n%s",
    "her_err_exportar": "El motor fallo al exportar:\n%s",
    "her_err_wannacri": "No encuentro wannacri (el extractor de .usm). No lo instalo solo: "
                        "esta en tools/wannacri del proyecto. Sin el no se pueden sacar los videos.",
    "her_err_ffmpeg": "No encuentro ffmpeg en el PATH. Sin el no se puede empaquetar el video.",
    "her_log_wannacri": "   wannacri: %s",
    "her_err_sin_pista": "wannacri no devolvio ninguna pista de video. Salida:\n%s",
    "her_log_ffmpeg": "   ffmpeg: %s -> %s",
    "her_err_ffmpeg_empaquetar": "ffmpeg fallo al empaquetar:\n%s",
    "her_log_video_listo": "   listo: %s (%.1f MB)",
    "her_log_audio_video": "   sonido del juego: banco %s, pista «%s»",
    "her_log_audio_video_mudo": "   sonido del juego: banco %s, pista «%s» — es silencio, se entrega el video mudo",
    "her_log_audio_video_no_hallado": "   sin sonido emparejado para %s (video mudo)",
    "her_log_audio_video_varios": "   %d pistas de audio en el MP4 (la 1.ª por defecto): %s",
    "her_log_audio_video_repetida": "   banco %s: es la misma pista que %s, no se duplica",
    "her_idioma_ja": "japones",
    "her_idioma_zh": "chino",
    "her_idioma_base": "base",
    "her_pista_sfx": "efectos (SFX)",
    "her_log_sin_cueinfo": "   no encuentro CueInfoMap.txt: no puedo emparejar el sonido",
    "her_log_hca": "   %d pista(s) HCA encontradas",
    "her_err_vgmstream": "No encuentro vgmstream-cli (el decodificador de HCA). No lo instalo "
                         "solo: esta en tools/vgmstream del proyecto. Sin el no se puede "
                         "decodificar el audio.",
    "her_log_wav": "   %s -> %s (%.1f MB)",
    "her_log_no_wav": "   no se pudo decodificar %s",
    "her_err_sin_audio": "vgmstream no decodifico ninguna pista del .awb.",
    "her_bundles_disco": "  —  listados desde la carpeta del juego",
    "her_sync_construir": "Construir indice",
    "her_sync_cancelar": "Cancelar",
    "her_sync_cancelando": "Cancelando el indice...",
    "her_sync_cancelado": "Indice cancelado: no se ha guardado nada.",
    "her_sync_progreso": "Analizando bundle %d de %d...",
    "her_sync_empezando": "Preparando el analisis...",
    "her_sync_confirmar": "El buscador global necesita analizar los %d bundles del juego con el "
                          "motor. Tarda decenas de minutos, pero solo se hace una vez: al "
                          "terminar se guarda junto al programa. Se puede cancelar en cualquier "
                          "momento. ¿Empezar ahora?",
    "her_sync_aviso": "El buscador global todavia no tiene su indice (%d bundles por analizar). "
                      "¿Construirlo ahora? Tarda decenas de minutos y se puede cancelar.",
    "her_sync_aviso_corto": "Buscador sin indice (%d bundles por analizar).",
    "her_sync_listo": "Indice listo: %d recursos en %d bundles.",
    "her_sync_parcial": "Indice PARCIAL: %d de %d bundles (%d recursos). Vuelve a construirlo para que busque en todo el juego.",
    "her_sync_hecho": "Indice construido: %d recursos.",
    "her_sync_guardado": "Indice guardado: %d recursos en %s",
    "her_sync_reutilizado": " (no ha hecho falta releer %d bundles: no cambiaron)",
    "her_sync_sin_bundles": "No encuentro bundles: elige primero la carpeta del juego.",
    "her_descargar_motor": "Descargar el motor",
    "her_deps_boton": "Descargar dependencias",
    "her_deps_titulo": "Descargando dependencias",
    "her_deps_peso": "Se van a bajar las herramientas que la app necesita (~%s MB en total). Esta ventana es solo para mirar: la consola no se puede escribir.",
    "her_deps_solo_ver": "Consola de solo lectura: puedes mirar el progreso, no escribir en ella.",
    "her_deps_cerrar": "Cerrar",
    "her_deps_confirmar": "Se van a descargar las herramientas externas (unos %s MB). ¿Seguimos?",
    "her_deps_listo": "Listo: las herramientas estan puestas.",
    "her_deps_fallo": "Se bajo el resto, pero algo fallo: %s",
    "her_deps_fuera": "Aviso: hay copias de fuera de la carpeta (la app las usa, pero no viajan con ella): %s",
    "her_motor_ya": "El motor ya esta instalado.",
    "her_motor_confirmar": "El inspector y las exportaciones necesitan el motor de extraccion "
                           "(AssetStudioModCLI, unos 16 MB). Se descarga de su pagina oficial en "
                           "GitHub y se guarda junto al programa. ¿Descargarlo ahora?",
    "her_motor_listo": "Motor listo: %s",

    # ---------------------------------------------------------------- ventana de solo herramientas
    "tools_lema": "Bundles, texturas y video/audio del juego, sin el apartado de modelos.",
    "tools_juego": "Juego:",
    "tools_elegir_juego": "Elegir carpeta del juego...",
    "tools_sin_juego": "no encontrado (elige la carpeta del juego)",
    "tools_carpeta_guardada": "Carpeta del juego guardada: %s\n%d bundles encontrados.",
    "tools_carpeta_no_valida": "Esa carpeta no es del juego. Busco dentro `Client/OuterPackage/"
                               "Bundles/Windows`.",
    "tools_log_titulo": "Actividad",
    "tools_herramientas_solo": "P5X Studio Tools",

    # ---------------------------------------------------------------- dependencias
    "dep_progreso_cmd": "> %s ...",
    "dep_creando_uv": "Creando el entorno con uv...",
    "dep_uv_fallo": "   uv fallo, se intenta con el Python del sistema",
    "dep_creando_sistema": "Creando el entorno con el Python del sistema...",
    "dep_err_entorno": "No se pudo crear el entorno: %s",
    "dep_err_python": "El entorno se creo pero no encuentro su python.",
    "dep_librerias_dentro": "Las librerias ya vienen dentro de la herramienta.",
    "dep_instalando": "Instalando lo que falta: %s",
    "dep_err_instalar": "No se pudieron instalar las librerias:\n%s",
    "dep_instaladas": "Instaladas.",
    "dep_descargando_motor": "Descargando el motor de extraccion...",
    "dep_descargando_pct": "   descargando: %d%%",
    "dep_descomprimiendo": "Descomprimiendo...",
    "dep_err_descargar": "No se pudo descargar el motor de extraccion (no hay conexion o "
                         "GitHub no responde).",
    "dep_err_motor_exe": "El motor se descargo pero no encuentro el ejecutable dentro.",
    "dep_motor_listo": "Motor listo (%s).",
    "dep_version_desconocida": "version desconocida",
    "dep_no_ejecutable": "no se encontro el ejecutable",
    "dep_tardo": "tardo demasiado",
    "dep_sin_instalar": "(sin instalar)",
    "dep_sin_instalar2": "sin instalar",
    "dep_nueva": "   %s: %s -> %s",
    "dep_err_actualizar": "No se pudo actualizar:\n%s",
    "dep_req_unitypy": "leer los ficheros del juego",
    "dep_req_pillow": "generar las vistas previas de los modelos",

    # ---------------------------------------------------------------- sesion de Unity
    "su_err_hub": "No he podido abrir el Unity Hub: %s",
    "su_msg_hub": "He abierto el Unity Hub.\n\nInicia sesion con tu cuenta (Unity Personal "
                  "es gratis) y, si te lo pide, activa la licencia para la version %s.\n\n"
                  "Cuando termines, pulsa Comprobar de nuevo: la licencia queda guardada y el "
                  "modo lote ya funcionara sin pedirte nada mas.",
    "su_msg_sin_hub": "No encuentro ni el Unity Hub ni el editor de Unity.\n\n"
                      "El editor esta instalado en este equipo, pero el Hub, que es quien activa "
                      "la licencia, no lo esta. Si no quieres instalarlo, abre el editor a mano "
                      "una vez y activa la licencia desde ahi.",
    "su_err_unity": "No he podido abrir Unity: %s",
    "su_msg_editor": "No encuentro el Unity Hub, asi que he abierto el editor directamente.\n\n"
                     "Si el editor no te ofrece iniciar sesion, instala el Unity Hub: es la via "
                     "normal para activar Unity Personal.\n\n"
                     "Cuando lo tengas, pulsa Comprobar de nuevo.",

    # ---------------------------------------------------------------- indice
    "ind_err_carpeta": "No se encuentra la carpeta de bundles del juego.",
    "ind_lista_oficial": "Leyendo la lista oficial de bundles...",
    "ind_recorriendo": "Recorriendo los ficheros descargados...",
    "ind_mapa": "Construyendo el mapa de nombres...",
    "ind_n_bundles": "   %d bundles en el manifiesto",
    "ind_n_ficheros": "   %d ficheros en disco",
    "ind_n_nombres": "   %d nombres logicos",
    "ind_guardado": "Indice guardado en %s",
    "ind_reconstruye": "El juego cambio desde el ultimo indice: se reconstruye.",

    # ---------------------------------------------------------------- unity (modo lote)
    "un_copiando": "Copiando el capturador al proyecto...",
    "un_arrancando": "Arrancando Unity en modo lote (la primera vez tarda un par de minutos)...",
    "un_err_no_editor": "no encuentro el Editor de Unity en este equipo",
    "un_err_capturador": "no encuentro el capturador %s dentro de la herramienta",
    "un_err_proyecto": "el proyecto de Unity no es valido: %s",
    "un_err_compila": "El proyecto de Unity no compila. Hay que neutralizar los scripts que "
                      "fallan (los del juego vienen como stubs de AssetRipper).",
    "un_revisa_log": "Revisa el log de Unity: %s",
    "un_volcado_listo": "Volcado listo: %d partes, %d con pesos, %d huesos unicos.",
    "un_err_volcado": "Unity no llego a volcar el esqueleto (codigo %d). %s",
    "un_err_malla": "Unity no monto ninguna malla del personaje %s (¿existe su prefab en el "
                    "proyecto?). Log: %s",

    # ---------------------------------------------------------------- glb_rig
    "gr_err_sin_esqueleto_json": "el volcado no trae esqueleto.json: ¿lo hizo el capturador de Unity?",
    "gr_err_sin_malla": "el volcado no trae ninguna malla",
    "gr_err_sin_hueso": "no se aprendio ningun hueso: revisa el volcado",
    "gr_huesos_mundo": "   huesos con mundo exacto (inversa de bind): %d",
    "gr_nodos": "   nodos de hueso: %d",
    "gr_huesos_cizalla": "   huesos sin padre (su matriz local llevaba cizalla): %d",
    "gr_huesos_espejo": "   huesos espejo enderezados (matriz de bind con determinante negativo): %d",
    "gr_glb_escrito": "3. GLB escrito: %s (%.2f MB)  huesos %d  mallas %d  con pesos %d  armaduras %d",
    "gr_ajuste": "   ajuste prefab->referencia: residuo mediana %.4f m  peor %.4f m",
    "gr_parte": "   %-22s verts %6d  huesos %4d  submallas %d  expresiones %d",
    "gr_aviso_huesos": "   aviso %s: %d huesos de la pieza sin equivalente",
    "gr_material_heredado": "   material heredado para %s: %s",

    # ---------------------------------------------------------------- fbx_blender
    "fb_args": "faltan argumentos: -- [--glb <glb>] [--obj <carpeta>]... <salida.fbx>",
    "fb_falta_salida": "falta la ruta del FBX de salida",
    "fb_armaduras": "[fbx] armaduras %d  huesos %d  mallas %d  con grupos de vertices %d",
    "fb_no_hay": "no hay GLB ni OBJ que importar",
    "fb_sin_glb": "[fbx] sin GLB: importando %d piezas OBJ (el FBX saldra sin esqueleto)",
    "fb_no_importo": "no se importo ninguna pieza",
    "fb_exportado_obj": "[fbx] exportado desde OBJ (sin esqueleto): %s",
    "fb_importando_glb": "[fbx] importando el GLB riggeado: %s",
    "fb_glb_sin_malla": "el GLB no trajo ninguna malla",
    "fb_exportado_glb": "[fbx] exportado desde el GLB: %s",
    "fb_no_importar": "[fbx] no se pudo importar %s (%s)",

    # ---------------------------------------------------------------- clave
    "cl_err_metadata": "No encuentro global-metadata.dat en la instalacion del juego.\n"
                       "Sin el no se puede descifrar los bundles.",
    "cl_calculando": "Calculando la clave de descifrado (puede tardar unos minutos, solo la "
                     "primera vez)...",
    "cl_obtenida": "Clave obtenida.",
    "cl_cache": "Clave de descifrado recuperada de la cache.",

    # ---------------------------------------------------------------- catalogo
    "ct_skin": "   (skin: sin cara propia)",
    "ct_escenario": "Escenario",
    "ct_objeto": "Objeto",
    "ct_efecto": "Efecto",
    "ct_personaje": "Personaje",

    # ---------------------------------------------------------------- nombres de traje
    "tr_normal": "Ropa normal",
    "tr_thief": "Traje de ladron",
    "tr_uniform": "Uniforme",
    "tr_uniform_swimsuit": "Banador (base uniforme)",
    "tr_thief_swimsuit": "Banador (base ladron)",
    "tr_swimsuit": "Banador",
    "tr_dress": "Vestido",
    "tr_catbag": "Disfraz de gato",
    "tr_autumn": "Ropa de otono",
    "tr_office": "Ropa de oficina",
    "tr_sports": "Ropa deportiva",
    "tr_maidsuit": "Traje de doncella",
    "tr_binghaofu": "Bata de hospital",
    "tr_wheelchair": "Silla de ruedas",
    "tr_gamer": "Ropa de gamer",
    "tr_doctor": "Bata de medico",
    "tr_student": "Uniforme escolar",
    "tr_velvet": "Terciopelo",
    "tr_heize": "Ropa negra",
    "tr_weiqun": "Falda",
    "tr_manwu": "Traje de baile",
    "tr_chushifu": "Bata de cocina",
    "tr_kokatsu": "Uniforme escolar",
    "tr_unreal": "Variante unreal",
    "tr_sp": "Variante SP",

    # ---------------------------------------------------------------- extractor
    "ex_falta_motor": "Falta el motor de extraccion. Pulsa «Actualizar librerias» en la "
                      "ventana principal para descargarlo.",
    "ex_motor_fallo": "El motor de extraccion fallo:\n%s",
    "ex_motor_ficheros": "   motor: %d ficheros de entrada procesados",
    "ex_progreso_fichero": "   (%d/%d) %s",
    "ex_no_procesar": "      no se pudo procesar este fichero: %s",
    "ex_sin_bundles": "No encuentro la carpeta de bundles del juego.",
    "ex_base_sin_ficheros": "no encuentro ningun fichero del modelo base %s",
    "ex_base_sin_cara": "el modelo base %s no trae cara ni ojos que se puedan usar",
    "ex_base_tomadas": "Modelo base %s: %d ficheros (grupo %s).",
    "ex_sin_ficheros": "No encuentro ningun fichero del personaje en disco.",
    "ex_traje_elegido": "Traje elegido: %s (%s).",
    "ex_vive_en": "El personaje vive en %d ficheros del juego.",
    "ex_extrayendo_de": "Extrayendo %s de %d ficheros (puede tardar unos minutos)...",
    "ex_motor_devolvio": "El motor devolvio %d mallas y %d texturas.",
    "ex_escenario_mallas": "Escenario con %d mallas: se dibujan las %d mas grandes.",
    "ex_no_dibujar": "   no se pudo dibujar %s (%s)",
    "ex_no_blender": "No encuentro Blender, asi que no puedo unir las piezas en un FBX. "
                     "Los OBJ estan completos y se abren igual.",
    "ex_blender_glb": "Blender esta montando el FBX desde el GLB riggeado (con esqueleto)...",
    "ex_blender_obj": "No hay GLB riggeado: Blender monta el FBX con los OBJ (saldra SIN "
                      "esqueleto, porque los OBJ no llevan huesos).",
    "ex_fbx_listo": "FBX listo: %s (%.1f MB%s)",
    "ex_con_esqueleto": ", con esqueleto",
    "ex_sin_esqueleto": ", sin esqueleto",
    "ex_blender_no_escribio": "Blender no llego a escribir el FBX: %s",
    "ex_no_fbx": "No se pudo crear el FBX (%s). Los OBJ estan completos.",
    "ex_esqueleto_respaldo_unity": "La lectura directa de los bundles no basto; se intenta montar "
                                   "el esqueleto dentro de Unity...",
    "ex_aviso_rig_bundles": "AVISO: no se pudo leer el esqueleto de los bundles (%s).",
    "ru_manifiestos": "Manifiestos de rig: %d; mallas con piel: %d.",
    "ru_jerarquia": "Jerarquia del actor: %d nodos.",
    "ru_parte": "Parte %s: %d vertices (%d con peso), %d huesos.",
    "ru_sin_manifiesto": "Sin manifiesto de huesos para %s; se omite.",
    "ex_esqueleto_listo": "Esqueleto y pesos listos: %d huesos y %d de %d mallas con grupos "
                          "de vertices (%s).",
    "ex_skin_tomado": "Este personaje es una skin: cara, ojos y pelo se han tomado del modelo "
                      "base %s (carpeta %s/). El cuerpo y la ropa son suyos.",
    "ex_aviso_sin_cara": "AVISO: este personaje no trae cara ni ojos.",
    "ex_aviso_skin": "Suele significar que es una SKIN: su cara esta en el modelo base, que son "
                     "otros bundles. El cuerpo, el pelo, las armas y las texturas que si trae "
                     "estan completos.",
    "ex_aviso_indicar_base": "Indica el modelo base de este personaje (buscador de base en la "
                             "interfaz) y la herramienta traera su cara, sus ojos y su pelo.",
    "ex_aviso_esqueleto_unity": "AVISO: no se pudo sacar el esqueleto con Unity (%s). El resto "
                                "del modelo esta completo.",
    "ex_aviso_glb": "AVISO: Unity volco los datos pero no se pudo armar el GLB (%s).",
    "ex_aviso_base": "AVISO: no se pudo traer el modelo base %s (%s).",
    "ex_sin_unity_editor": "No hay Editor de Unity instalado: el modelo se entrega con "
                           "geometria, texturas y materiales, pero sin esqueleto ni pesos de piel.",
    "ex_sin_proyecto_unity": "No encuentro el proyecto de Unity decompilado (hace falta para "
                             "sacar el esqueleto). Se le puede indicar en la configuracion de "
                             "la herramienta, con la clave «proyecto_unity».",
    "ex_ensamblando_glb": "Ensamblando el GLB con el esqueleto...",
    "ex_localizando": "Localizando los ficheros del personaje...",
    "ex_geometria": "Extrayendo la geometria y las texturas...",
    "ex_ordenando": "Ordenando lo extraido...",
    "ex_trayendo_base": "Trayendo la cara, los ojos y el pelo del modelo base...",
    "ex_esqueleto": "Sacando el esqueleto y los pesos de piel...",
    "ex_rigs": "Sacando los rigs del juego...",
    "ex_tabla": "Preparando la tabla de texturas...",
    "ex_previas": "Dibujando las vistas previas...",
    "ex_fbx": "Creando el FBX final...",
    "ex_escribiendo": "Escribiendo el resumen...",
    "ex_terminado": "Terminado.",
    "ex_listo_en": "Listo en %.1f segundos.",
    "ex_mapa_extra": "# mapa adicional del juego: %s",
    "ex_base_parte_linea": "%s (%d mallas)",
    "ex_leeme_base":
        "# Piezas tomadas del modelo base\n\n"
        "Este personaje es una SKIN: el juego no le pone cara. La cara, los ojos (con parpados) y el\n"
        "pelo se han tomado del modelo base **%s**.\n\n"
        "- Base: `%s` (grupo: %s)\n"
        "- Piezas tomadas: %s\n"
        "- Bundles de origen: %s\n\n"
        "El cuerpo, la ropa y las armas que hay en `01_model/` y `02_textures/` son de la skin; lo de\n"
        "esta carpeta viene del base.\n",
    "prev_titulo": "%s - %s",
    "prev_titulo_lamina": "%s (%s)",
    "prev_titulo_base": "%s (modelo base) - %s",
    "prev_lamina_base": "%s - cara, ojos y pelo del base %s",
    "ex_rigs_sueltos": "Rigs sueltos exportados: %d.",
    "ex_no_rigs": "No se pudieron sacar los rigs sueltos (%s).",
    "ex_rigs_dentro": "Este personaje no trae rigs aparte: los huesos van dentro de los "
                      "propios OBJ.",
    "ex_del_base": "Del base: %d mallas y %d texturas de cara, ojos y pelo.",

    # extractor: nombres de parte
    "ex_parte_body": "Cuerpo y ropa",
    "ex_parte_face": "Cara",
    "ex_parte_hair": "Pelo",
    "ex_parte_eyes": "Ojos",
    "ex_parte_weapons": "Armas",
    "ex_parte_other": "Otros",

    # extractor: ficheros que escribe
    "ex_leeme": "Las expresiones faciales del juego son morphs (formas de la malla) y el formato OBJ no\n"
                "las puede guardar. Se conservan si se exporta la malla a FBX o se abre en Unity.\n"
                "Las piezas de la cara que sí se han extraido estan en 01_model/obj/face/.\n",
    "ex_tabla_titulo": "# Piezas y texturas",
    "ex_tabla_cab": "| malla | origen | material | texturas |",
    "ex_readme_intro": "Modelo extraido del juego con P5X Studio %s el %s.",
    "ex_readme_traje": "**Traje:** %s (`%s`). Este modelo trae SOLO este traje del personaje.",
    "ex_readme_tipo": "**Tipo:** %s. Es un bundle del juego convertido en entrada extraible: "
                      "trae sus propias mallas y texturas. No es un personaje, asi que no lleva "
                      "cara, esqueleto ni modelo base.",
    "ex_readme_previas_lim": "**Vistas previas:** el escenario tiene %d mallas; se han dibujado "
                             "las %d mas grandes. Las demas estan igualmente en `01_model/obj/`.",
    "ex_readme_que_hay": "## Que hay dentro",
    "ex_readme_carpeta_cont": "| carpeta | contenido |",
    "ex_readme_glb_row": "| `<nombre>.glb` | **EL MODELO**: malla, UVs, texturas incrustadas, "
                         "esqueleto y pesos de piel en un solo fichero. Es el que hay que abrir |",
    "ex_readme_fbx_all": "| `<nombre>_full.fbx` | el mismo modelo en FBX, con armadura y pesos, "
                         "por si el programa de destino prefiere FBX |",
    "ex_readme_01": "| `01_model/obj/` | la geometria suelta en OBJ, un fichero por pieza (solo "
                    "geometria y UVs: sin huesos ni pesos) |",
    "ex_readme_02": "| `02_textures/` | las texturas en PNG, las mismas que van incrustadas en el GLB |",
    "ex_readme_03": "| `03_skeleton/` | detalle del esqueleto y los recuentos (`esqueleto.json`) |",
    "ex_readme_04": "| `04_expressions/` | nota sobre las expresiones (ver LEEME.txt) |",
    "ex_readme_05": "| `05_materials/` | que textura usa cada pieza |",
    "ex_readme_prev": "| `preview/` | vistas previas (empieza por `lamina_completa.png`) |",
    "ex_readme_weapons": "| `01_model/obj/weapons/<arma>/` | cada arma en su carpeta, con sus "
                         "texturas en `02_textures/weapons/<arma>/` |",
    "ex_readme_other": "| `01_model/obj/other/<prop>/` | cada prop en su carpeta, con sus "
                       "texturas en `02_textures/other/<prop>/` |",
    "ex_readme_base_row": "| `%s/` | cara, ojos y pelo tomados del modelo base %s |",
    "ex_readme_fbx_rig": "| | el FBX lleva la armadura y los pesos de piel, igual que el GLB |",
    "ex_readme_fbx_norig": "| | el FBX se ha montado con los OBJ y por eso NO lleva esqueleto |",
    "ex_readme_piezas": "## Piezas encontradas",
    "ex_readme_parte_cab": "| parte | mallas | texturas |",
    "ex_readme_base_titulo": "## Modelo base",
    "ex_readme_base_1": "Este personaje es una SKIN: el juego no le pone cara. La cara, los ojos (con",
    "ex_readme_base_2": "parpados) y el pelo se han tomado del modelo base **%s** y estan en la carpeta",
    "ex_readme_base_3": "`%s/`, separados de lo que trae la skin. Bundles del base:",
    "ex_readme_base_parte": "- %s del base: %d mallas, %d texturas",
    "ex_readme_abrir": "## Como abrirlo",
    "ex_readme_abrir_txt": "Abre el `<nombre>.glb` de esta carpeta: en Blender (Archivo > Importar > "
                           "glTF 2.0) o en cualquier visor de modelos. Lleva dentro la malla, las "
                           "UVs, las texturas, el esqueleto y los pesos, asi que se ve montado y "
                           "con sus colores sin tocar nada mas. El FBX es el mismo modelo por si tu "
                           "programa prefiere ese formato; los OBJ de `01_model/obj/` son solo la "
                           "geometria suelta (sin huesos) para retoques puntuales.",
    "ex_readme_lod": "Las piezas cuyo nombre termina en `_lod` o `_shadow` son copias de baja "
                     "calidad o auxiliares del juego: puedes ignorarlas.",
    "ex_readme_armas_props": "Cada arma y cada prop esta en su propia carpeta dentro de "
                             "`01_model/obj/`, y su MTL apunta solo a las texturas de esa pieza, "
                             "guardadas junto a ella en `02_textures/`: asi las texturas de un "
                             "arma no se mezclan con las del cuerpo.",
    "ex_readme_esq_titulo": "## Esqueleto y pesos de piel",
    "ex_readme_esq_1": "El modelo riggeado es `<nombre>.glb`, en la raiz de esta carpeta, y se abre "
                       "directamente en Blender o en cualquier visor glTF, con su armadura y sus "
                       "pesos de piel.",
    "ex_readme_huesos": "- huesos: %d",
    "ex_readme_pesos": "- mallas con pesos: %d de %d",
    "ex_readme_morphs": "- expresiones faciales (morphs): %d",
    "ex_readme_hecho_unity": "- hecho con Unity %s (modo lote) sobre el proyecto decompilado del juego",
    "ex_readme_fbx_rig2": "El FBX `<nombre>_full.fbx` lleva esa misma armadura y esos mismos "
                          "pesos: se abre en Blender con su esqueleto ya montado.",
    "ex_readme_esq_2": "Los huesos y los pesos se leen de los propios bundles del juego (la malla "
                       "trae la piel y las inversas de bind; el prefab del actor, la jerarquia; y "
                       "el manifiesto del rig, el orden de huesos por malla). No hace falta Unity.",
    "ex_readme_hecho_bundles": "- leido de los bundles del juego (sin Unity)",
    "ex_readme_aviso": "## Aviso",
    "ex_readme_aviso_txt": "Material extraido del juego para uso personal y de investigacion. "
                           "No redistribuir los recursos originales.",
    "ex_readme_tipo_escenario": "escenario del juego",
    "ex_readme_tipo_objeto": "objeto o prop del juego",
    "ex_readme_tipo_efecto": "efecto del juego",
    "ex_readme_tipo_modelo": "modelo del juego",

    # ---------------------------------------------------------------- texturas en bloque (bulk)
    "web_bulk_tab": "Texturas en bloque",
    "web_bulk_titulo": "Texturas en bloque",
    "web_bulk_ayuda": "Saca las texturas de TODOS los bundles del juego y las ordena en carpetas por "
                      "categoria. Cada textura acaba en Categoria/conjunto, donde conjunto es el "
                      "bundle del que sale.",
    "web_bulk_col_categoria": "Categoria",
    "web_bulk_col_bundles": "Bundles",
    "web_bulk_col_texturas": "Texturas",
    "web_bulk_col_peso": "Peso aprox.",
    "web_bulk_filtro": "Filtro por texto",
    "web_bulk_filtro_ayuda": "Saca solo las texturas cuyo nombre contenga esto (p. ej. PC079 para un "
                             "personaje, scn11 para un escenario, item). Vacio = todo.",
    "web_bulk_sprites": "Incluir sprites de la interfaz (trozos recortados de los atlas)",
    "web_bulk_por_tipo": "Separar por tipo de mapa (Color / Normal / Emision / Lightmap...)",
    "web_bulk_destino": "Carpeta destino",
    "web_bulk_elegir": "Elegir...",
    "web_bulk_libre": "%s libres en ese disco",
    "web_bulk_empezar": "Extraer lo marcado",
    "web_bulk_cancelar": "Cancelar",
    "web_bulk_ya_hecho": "%s bundles ya hechos en este destino: al relanzar sigue desde ahi.",
    "web_bulk_estimado": "Estimado: %s texturas, ~%s MB.",
    "web_bulk_estimado_filtro": "Con filtro no se puede estimar de antemano.",
    "web_bulk_aviso": "Solo arranca cuando pulses el boton, y se puede cancelar y seguir luego.",
    "web_bulk_vacio": "Todavia no hay nada extraido en esta carpeta.",
    "web_bulk_abrir": "Abrir la carpeta",
    "web_bulk_reanudar": "Continuar por lo que ya esta hecho (recomendado)",
    "web_bulk_todo": "Todo",
    "web_bulk_nada": "Nada",
    "web_bulk_progreso": "%s / %s bundles",
    "web_bulk_consola": "Lo que va pasando",
    "bulk_log_pasada": "Exportando el lote %s (%d bundles)...",
    "bulk_log_arranca": "Texturas en bloque: %d bundles. Categorias: %s",
    "bulk_log_lote": "%s: %d/%d bundles, %d ficheros en su sitio",
    "bulk_log_fallo": "%s: fallo -> %s",
    "bulk_log_fin": "Hecho: %d texturas ordenadas en sus carpetas.",
    "bulk_log_cancelado": "Cancelado en %d/%d bundles (lo hecho queda apuntado).",
    "bulk_err_motor": "El motor fallo al exportar el lote: %s",
    "bulk_err_sin_categoria": "No hay ninguna categoria marcada.",
    "bulk_err_lote_vacio": "%s: no he podido preparar el lote (bundles no encontrados).",
    "bulk_fin": "Hecho: %s texturas.",
    "bulk_fin_cancelado": "Cancelado: %s texturas.",
    "bulk_err_espacio": "No hay sitio: hacen falta ~%s MB y quedan %s MB libres.",
    "web_bust_tab": "Bust-ups",
    "web_bust_title": "Visor de bust-ups",
    "web_bust_sub": "Los retratos del dialogo, montados capa a capa con las texturas que has extraido.",
    "web_bust_ph": "busca un personaje…",
    "web_bust_expression": "Expresion",
    "web_bust_shader": "Shader",
    "web_bust_tinte": "Tinte",
    "web_bust_export": "Exportar PNG",
    "web_bust_reveal": "Ver en la carpeta",
    "web_bust_working": "Montando…",
    "web_bust_n": "%s bust-ups",
    "web_bust_none": "No hay texturas. Dale a «Extraer retratos» (unos 170 MB) o pasa el lote de texturas entero.",
    "web_bust_elegir": "Elegir carpeta…",
    "web_bust_capas": "Capas",
    "web_bust_avisos": "Avisos",
    "web_bust_exportado": "Guardado en %s",
    "web_bust_medido": "posicion medida comparando pixeles (difiere %s%)",
    "web_bust_sin_cuerpo": "Este bust-up no tiene capa de cuerpo en la carpeta de texturas.",
    "web_bust_no_fiable": "hoja propia: posicion deducida",
        "web_bust_defecto": "Por defecto",
                "web_bust_aviso_hoja": "Las capas cuya hoja no es el lienzo del retrato se dejan fuera (sin el prefab no se puede saber donde van).",
                "web_bust_retr_titulo": "Texturas de retrato",
                "web_bust_retr_nota": "El visor solo necesita los retratos de dialogo: unos 170 MB, en vez de los 63 GB del bulk entero.",
                "web_bust_retr_boton": "Extraer retratos",
                "web_bust_retr_parar": "Parar",
                "web_bust_retr_nada": "Sin texturas de retrato todavia.",
                "web_bust_retr_listo": "Retratos listos: %s PNG · %s MB",
                "web_bust_retr_progreso": "Sacando retratos: %s/%s bundles",
                "web_bust_retr_fin": "%s PNG guardados · %s MB",
                "web_bust_retr_bulk": "usando el bulk entero (%s)",
                "web_bust_retr_carpeta": "carpeta: %s",
                "retr_log_arranca": "Retratos: %s bundles de texturas de interfaz",
                "retr_log_lote": "   retratos: %s/%s bundles · %s PNG guardados",
    }


# =========================================================================== INGLES
EN = {
    # ---------------------------------------------------------------- new interface (web)
    "web_brand_sub": "Tools",
    "web_nav_bundles": "Bundles",
    "web_nav_inspector": "Inspector",
    "web_nav_resources": "Resources",
    "web_nav_textures": "Textures",
    "web_nav_media": "Video & audio",
    "web_foot_index": "Index: %s bundles",
    "web_loading": "Loading…",
    "web_error": "Error: %s",
    "web_soon_title": "Under construction",
    "web_soon_body": "This screen isn't wired to the engine yet. No made-up data is shown.",
    "web_note": "Data comes from your copy of the game. Nothing is invented: what isn't known is left blank.",

    # --- explorer
    "web_explore_title": "Explore the game's bundles",
    "web_explore_sub": "Search by name, filter by type, and read what's inside without opening anything.",
    "web_search_placeholder": "part_l_normal, shared_, scn_hougewai…",
    "web_chip_all": "All",
    "web_new": "New",
    "web_new_only": "Only new",
    "web_new_mark": "Mark as seen",
    "web_new_done": "%s bundles marked as seen",
    "web_results": "Results",
    "web_shown": "%s of %s shown",
    "web_empty": "Nothing matches that search.",
    "web_source_disk": "Read from the game folder, without an index.",
    "web_unit_mesh": "mesh",
    "web_unit_mesh_pl": "meshes",
    "web_unit_tex": "tex",
    "web_d_meshes": "Meshes",
    "web_d_textures": "Textures",
    "web_d_size": "Size",
    "web_d_type": "Type",
    "web_d_contents": "Contents",
    "web_d_open": "Open with the engine",
    "web_d_extract": "Extract this bundle",
    "web_d_reveal": "Reveal in folder",
    "web_d_close": "Close",
    "web_d_actors": "Actors",
    "web_d_costumes": "Outfits",
    "web_d_role": "Role",
    "web_d_what": "What it is",
    "web_none": "—",

    # --- inspector
    "web_insp_title": "Inspect a bundle",
    "web_insp_sub": "Open a bundle with the engine and see what resources it holds, by name and type.",
    "web_insp_path": "Bundle path",
    "web_insp_ph": "110/shared_....bundle",
    "web_insp_open": "Open with the engine",
    "web_insp_choose": "Choose file…",
    "web_col_name": "Name",
    "web_col_type": "Type",
    "web_col_container": "Container",
    "web_col_pathid": "PathID",
    "web_col_size": "Size",
    "web_insp_export": "Export selected",
    "web_insp_export_all": "Export all (meshes + textures)",
    "web_insp_empty": "Open a bundle to see what it holds.",
    "web_insp_working": "Opening…",
    "web_insp_n": "%s resources",

    # --- resource search
    "web_res_title": "Resource search",
    "web_res_sub": "Search a mesh or texture by name across the WHOLE game.",
    "web_res_ph": "mesh or texture name…",
    "web_res_build": "Build index",
    "web_res_rebuild": "Rebuild",
    "web_res_cancel": "Cancel",
    "web_res_none": "There's no search index yet.",
    "web_res_none_body": "Building it opens every bundle with the engine; with all 16,535 it takes about 29 minutes. You can cancel, and a partial run isn't saved.",
    "web_res_building": "Building index: %s / %s",
    "web_res_ready": "Index ready: %s resources in %s bundles.",
    "web_res_parcial": "PARTIAL index: covers %s of %s bundles (%s resources). Build it again to search the whole game.",
    "web_res_cancelled": "Cancelled. Nothing was saved.",
    "web_res_empty": "Nothing matches.",
    "web_col_bundle": "Bundle",

    # --- textures
    "web_tex_title": "Texture viewer",
    "web_tex_sub": "See the images that come out of an extraction, without leaving the app.",
    "web_tex_bundle": "Bundle to extract from",
    "web_tex_export": "Extract textures",
    "web_tex_folder": "Folder with images",
    "web_tex_choose": "Choose folder…",
    "web_tex_scan": "Find images",
    "web_tex_none": "No images in that folder. Extract textures from a bundle or pick another folder.",
    "web_tex_n": "%s images",
    "web_tex_working": "Extracting…",

    # --- video & audio
    "web_media_title": "Video & audio",
    "web_media_sub": "The client's videos and music. Extracting a video keeps ALL of its audio tracks.",
    "web_media_videos": "Videos",
    "web_media_audios": "Audio",
    "web_media_list": "List",
    "web_media_none": "I can't find the game's media folder.",
    "web_media_n": "%s files",
    "web_media_extract_video": "Extract MP4",
    "web_media_extract_audio": "Extract WAV",
    "web_media_open_out": "Open output folder",
    "web_media_working": "Extracting…",
    "web_media_done": "Done: %s",
    "web_deps_btn": "Dependencies",
    "web_nav_settings": "Settings",
    "web_settings_title": "Settings",
    "web_settings_sub": "Customize the theme, game paths and tool options.",
    "web_theme_label": "Theme",
    "web_theme_desc": "Choose the color palette for the interface.",
    "web_settings_game_path": "Game installation",
    "web_settings_game_desc": "The P5X game folder being scanned. If auto-detection fails or you have multiple installations, choose the correct one.",
    "web_settings_choose_game": "Choose folder…",
    "web_settings_detect": "Auto-detect",
    "web_settings_game_ok": "Game detected — Steam (Global)",
    "web_settings_tex_path": "Texture folder",
    "web_settings_tex_desc": "Where extracted portrait textures are stored.",
    "web_settings_choose_tex": "Choose folder…",
    "web_settings_tex_ok": "3,258 sprites found",
    "web_settings_out_path": "Output folder",
    "web_settings_out_desc": "Where exported bust-ups and textures are saved.",
    "web_settings_choose_out": "Choose folder…",
    "web_settings_about": "About",
    "web_settings_version": "Version",
    "web_settings_bundles": "Bundles indexed",
    "web_settings_bustups": "Bust-ups available",
    "web_settings_shaders": "Shader profiles",
    "web_settings_thumbs": "Thumbnails",
    "web_deps_title": "Dependencies",
    "web_deps_peso": "These tools are needed (~%s MB in total). The app downloads them into tools/.",
    "web_deps_bajar": "Download dependencies",
    "web_deps_solo_ver": "This console is read-only: you can't type in it.",
    "web_deps_cerrar": "Close",
    "web_deps_uv": "uv (sets up the wannacri environment)",
    "web_deps_motor": "Engine (reads the bundles)",
    "web_deps_wannacri": "wannacri (pulls the video out of .usm)",
    "web_deps_vgmstream": "vgmstream (reads the audio of .acb)",
    "web_deps_ffmpeg": "ffmpeg (builds the MP4)",
    "web_deps_si": "installed",
    "web_deps_no": "missing",
    "web_deps_fuera": "outside the folder",
    "web_deps_fuera_ayuda": "The app is using it from outside the folder (it won't travel with it): the button downloads its own copy.",
    "web_deps_listo": "Done: %s tools.",
    "web_deps_fallo": "The rest downloaded, but something failed:",
    "dep_motor_ajeno": "You have a copy of the engine outside the tool (%s); I'm downloading my own so the folder works on another machine.",
    "web_media_legend": "Audio tracks are tagged: jpn (Japanese), chi (Chinese) and und (effects, no voice). «sin_dato» means it can't be known without decoding; that's the truth, not an error.",
    "web_audio_audio": "with audio",
    "web_audio_silencio": "silence",
    "web_audio_mudo": "no audio",
    "web_audio_sin_dato": "sin_dato",

    # ---------------------------------------------------------------- comun
    "comun_todo": "All",
    "comun_buscar": "Search",
    "comun_comprobando": "checking...",
    "comun_idioma": "Language:",
    "comun_idioma_nombre": "English",

    # ---------------------------------------------------------------- cabecera
    "cab_lema": "Extract the game's models and keep them organised, with their textures "
                "and previews.",

    # ---------------------------------------------------------------- pestanas
    "tab_extraccion": "  Extraction  ",
    "tab_herramientas": "  Tools  ",

    # ---------------------------------------------------------------- panel de estado
    "est_titulo": "Status",
    "est_comprobar": "Check again",
    "est_juego": "Game installation",
    "est_librerias": "Required libraries",
    "est_indice": "Model index",
    "est_esqueleto": "Skeleton (Unity)",
    "est_encontrado": "found: %s",
    "est_no_encontrado": "not found: use the button to point to the folder",
    "est_listas": "ready",
    "est_personajes": "%d characters",
    "est_unity_ok": "ready: editor, licence and project",
    "est_esqueleto_bundles": "ready: bones and weights straight from the game bundles",
    "est_esqueleto_bundles_unity": "ready from the bundles (Unity also available as fallback)",
    "est_unity_sin_editor": "no Unity editor: there will be no skeleton or skin weights",
    "est_unity_sin_licencia": "licence missing: click «Sign in to Unity»",
    "est_unity_sin_proyecto": "the game's decompiled Unity project is missing",
    "btn_elegir_carpeta": "Choose game folder",
    "btn_actualizar_librerias": "Update libraries",
    "btn_sesion_unity": "Sign in to Unity",

    # ---------------------------------------------------------------- barra de accion
    "pie_extraer": "Extract model",
    "pie_abrir": "Open the model folder",
    "pie_listo": "Ready to start.",
    "pie_extraido": "Model extracted.",
    "pie_error": "Could not complete.",

    # ---------------------------------------------------------------- eleccion de personaje
    "lista_paso1": "1. Find the character",
    "lista_mostrar": "Show:",
    "lista_cuenta": "%d in the list",
    "traje_label": "Outfit:",
    "traje_cuenta": "%d outfits: pick one",
    "traje_valor": "%s  (%d meshes, %d textures)",

    # ---------------------------------------------------------------- categorias
    "cat_personaje": "Characters",
    "cat_objeto": "Objects",
    "cat_escenario": "Scenes",
    "cat_efecto": "Effects",
    "cat_camara": "Cameras",
    "cat_valor": "%s (%d)",

    # ---------------------------------------------------------------- opciones
    "opt_titulo": "2. Choose what to extract",
    "opt_mallas": "Models (geometry)",
    "opt_texturas": "Textures",
    "opt_materiales": "Materials",
    "opt_esqueleto": "Skeleton and expressions",
    "opt_previas": "Previews",
    "opt_fbx": "FBX with everything joined",
    "opt_armas": "Include the character's weapons",
    "opt_paso3": "3. Extract",
    "opt_pie": "Click the «Extract model» button at the very bottom.",
    "base_titulo": "4. Base model (for skins)",
    "base_vacio": "Pick a character from the list.",
    "base_fijar": "Set as base",
    "base_quitar": "Remove",

    # ---------------------------------------------------------------- registro
    "log_titulo": "What's happening",

    # ---------------------------------------------------------------- mensajes de la ventana
    "msg_ocupado": "A task is already running. Wait for it to finish.",
    "msg_no_completar": "Could not complete.",
    "msg_no_completar_detalle": "Could not complete: %s",
    "msg_extraido_titulo": "Model extracted successfully.\n\nSaved to:\n%s",
    "msg_listo_en": "Done. The model is at: %s",
    "log_comprobando_instalacion": "Checking the installation...",
    "log_juego_encontrado": "  Game found at %s",
    "log_juego_no": "  I can't find the game. You can point to it by hand.",
    "log_preparando_librerias": "Preparing the libraries...",
    "log_leyendo_indice": "Reading the model index...",
    "log_todo_listo": "All set. You can now search for a character.",
    "estado_elige_extraer": "Pick a character and press Extract.",
    "log_aviso": "Warning: %s",
    "estado_revisa_avisos": "Check the warnings above.",
    "msg_unity_ya": "Unity already has a saved licence. Skeleton and skin-weight extraction "
                    "will work without asking you anything.",
    "msg_unity_sin_editor": "I can't find the Unity editor on this machine.\n\n"
                            "It's needed to get the skeleton and the weights, the only thing "
                            "that can't be obtained from the bundles. Without it, the tool gives "
                            "you geometry, textures, materials and the joined FBX, but not the rig.",
    "dlg_carpeta_juego_titulo": "Choose the game folder (the one containing Client)",
    "msg_carpeta_no_valida": "That folder isn't the game's.\n\n"
                             "Choose the folder containing «Client\\OuterPackage\\Bundles\\Windows», "
                             "or that bundles folder itself.\n\n"
                             "I haven't saved it. Nothing needs decompiling or deobfuscating: the "
                             "engine reads the bundles as they are, with their name as it comes.",
    "log_carpeta_fijada": "Game folder set to: %s",
    "log_bundles_encontrados": "  bundles found: %d",
    "msg_carpeta_guardada": "Game folder saved.\n\n%s\n\nFound %d bundles. "
                            "It will be remembered next time you open the tool.",
    "log_buscando_versiones": "Looking for new versions...",
    "log_todo_aldia": "Everything is up to date.",
    "msg_hay_nuevas": "New versions available for: %s\n\nUpdate them now?",
    "log_librerias_actualizadas": "Libraries updated.",
    "log_no_actualizar": "Could not update: %s",

    # ---------------------------------------------------------------- detalle de la lista
    "det_ficha": "%s: %d files (%s)",
    "det_trae": "   includes: %s",
    "det_skin": "   NOTE: this is a skin. Its face lives in the base model, which is other "
                "bundles; whatever comes out here won't have a face.",
    "det_otros": "   (%d more files that are NOT part of the model: timelines, scenes or "
                 "effects; they are not extracted)",
    "det_trajes": "   outfits: %s",
    "det_traje_aviso": "   the outfit chosen in the «Outfit» dropdown will be extracted.",
    "det_traje_elegido": "   chosen outfit: %s (%d files)",
    "det_base_declarado": "   declared base model: %s",
    "det_base_posible": "   possible base model (click «Set as base»): %s -> %s",
    "det_base_fijado": "   base %s declared for %s.",
    "det_base_quitado": "   base removed from %s.",

    # ---------------------------------------------------------------- modelo base
    "base_msg_no_personaje": "Not a character: it doesn't need a base model.",
    "base_msg_declarado": "Declared base: %s (%s).",
    "base_msg_propia": "This character already has its own face: it doesn't need a base.",
    "base_msg_posible": "Skin with no declared base. Possible base: %s.",
    "base_msg_sin_pista": "Skin with no declared base and no clear hint: search for the base by hand.",
    "base_err_corto": "Type at least two letters of the base's name.",
    "base_err_buscar": "I couldn't search: %s",
    "base_marca_cara": "FACE",
    "base_lista_vacia": "  (nothing with a face; try another part of the name)",
    "base_err_sin_personaje": "First pick the character from the list.",
    "base_err_sin_seleccion": "Pick a base model from the list below first.",
    "base_err_faltan": "The character and its base model are both required.",
    "base_err_propio": "A model can't be its own base.",
    "base_motivo": "appears in: %s",

    # ---------------------------------------------------------------- extraccion
    "extraer_err_sin_personaje": "First pick a character from the list.",
    "extraer_err_sin_indice": "I'm still preparing the index. One moment.",
    "extraer_pregunta_unity": "The skeleton and skin weights need Unity in batch mode, and "
                              "right now that's not possible:\n\n%s.\n\n"
                              "The rest of the model (geometry, textures, materials and the "
                              "joined FBX) can be extracted without Unity, but the model won't "
                              "come out rigged.\n\nExtract the model without a skeleton?",

    # ---------------------------------------------------------------- HERRAMIENTAS
    "her_titulo": "Game tools",
    "her_lema": "Browse the 16,535 bundles, open one with the engine, search any "
                "resource by name and pull videos and music from the client.",
    "her_tab_explorador": "  Bundle explorer  ",
    "her_tab_inspector": "  Bundle inspector  ",
    "her_tab_buscador": "  Resource search  ",
    "her_tab_texturas": "  Texture viewer  ",
    "her_tab_media": "  Video and audio  ",

    "her_tipo": "Type:",
    "her_actor": "Actor:",
    "her_traje": "Outfit:",
    "her_min_mb": "Min. MB:",
    "her_filtrar": "Filter",
    "her_bundles_de": "%d bundles (of %d)",
    "her_solo_4000": "  — only the first 4000 are shown",
    "her_col_bundle": "Bundle",
    "her_col_tipo": "Type",
    "her_col_papel": "Role",
    "her_col_mb": "MB",
    "her_col_mallas": "Meshes",
    "her_col_texturas": "Textures",
    "her_col_contenido": "Content",
    "her_ver_dentro": "Look inside",
    "her_exportar_mesh_tex": "Export meshes + textures",
    "her_det_tipo_papel": "type: %s   role: %s",
    "her_det_que_es": "what it is: %s",
    "her_det_tamano": "size: %.2f MB",
    "her_det_actores": "actors: %s",
    "her_det_trajes": "outfits: %s",
    "her_det_quien": "who: %s",
    "her_det_contenido": "content: %s",
    "her_det_mallas": "meshes (%d): %s",
    "her_det_texturas": "textures (%d): %s",

    "her_bundle": "Bundle:",
    "her_elegir_fichero": "Choose file...",
    "her_abrir_motor": "Open with the engine",
    "her_col_nombre": "Name",
    "her_col_tipo2": "Type",
    "her_col_contenedor": "Container",
    "her_col_pathid": "PathID",
    "her_col_tamano": "Size",
    "her_exportar": "Export:",
    "her_mallas": "Meshes",
    "her_texturas": "Textures",
    "her_mallas_texturas": "Meshes + textures",
    "her_todo_posible": "Everything possible",
    "her_msg_ruta": "Type or choose the path of a bundle.",
    "her_abriendo": "Opening with the engine...",
    "her_recursos_dentro": "   %d resources inside %s",
    "her_n_recursos": "%d resources",
    "dlg_bundle_titulo": "Choose a game bundle",
    "dlg_bundle_unity": "Unity bundles",
    "dlg_bundle_todos": "All",

    "her_recurso": "Resource:",
    "her_col_recurso": "Resource",
    "her_col_tipo3": "Type",
    "her_col_bundle": "Bundle",
    "her_coincidencias": "%d matches (index of %d resources)",
    "her_msg_dos_letras": "Type at least two letters of the name.",
    "her_log_buscador": "Search: «%s» -> %d matches",
    "her_ver_bundle": "View the bundle",
    "her_exportar_bundle": "Export the bundle",

    "her_carpeta": "Folder:",
    "her_elegir_carpeta": "Choose folder...",
    "her_listar_imagenes": "List images",
    "dlg_carpeta_img_titulo": "Folder with extracted images",
    "her_elige_imagen": "Pick an image from the list.",
    "her_n_imagenes": "%d images in the folder.",
    "her_sin_imagenes": "No images here.\nExport something and list again.",
    "her_sin_pillow": "Pillow is missing: %s",
    "her_err_imagen": "Could not open this image:\n%s",

    "her_herr_externas": "External tools",
    "her_herr_ok": "✓ %s",
    "her_herr_no": "✗ missing %s",
    "her_wannacri": "wannacri (.usm -> video)",
    "her_vgmstream": "vgmstream (.awb -> wav)",
    "her_ffmpeg": "ffmpeg (pack video)",
    "her_motor": "AssetStudio engine (bundles)",
    "her_comprobar_herr": "Check tools",
    "her_mostrar": "Show:",
    "her_videos": "Videos (.usm)",
    "her_audios": "Audio (.awb)",
    "her_listar": "List",
    "her_extraer_elegido": "Extract the selected one",
    "her_media_ayuda": "MP4 with sound; tracks labelled. Loose audio: WAV.",
    "her_extraer_mp4": "Extract to MP4",
    "her_extraer_wav": "Extract to WAV",
    "her_abrir_salida": "Open the output folder",
    "her_no_carpeta_media": "I can't find the client's video and audio folder.",
    "her_log_no_media": "Video and audio: I can't find Client/OuterPackage/Media/Windows.",
    "her_ficheros_en": "%d files in %s",
    "her_media_resumen": "%d with audio · %d silent · %d no audio",
    "her_video_con_audio": "♪ with audio",
    "her_video_sin_audio": "— no audio",
    "her_video_silencio": "⚠ silent",
    "her_video_sin_dato": "? no data",
    "her_leyenda_audio": "Audio badge (before extracting): ♪ with audio  ·  — no audio  ·  "
                         "⚠ the track exists but is silence.",
    "her_msg_elige_fichero": "Pick a file from the list first.",
    "her_log_extrayendo_video": "Extracting video: %s",
    "her_estado_video_listo": "Video ready: %s",
    "her_log_video_extraido": "Video extracted: %s",
    "her_log_extrayendo_audio": "Extracting audio: %s",
    "her_estado_audio_listo": "%d audio track(s) ready",
    "her_exportando": "Exporting %s...",
    "her_log_exportando": "Exporting %s -> %s",
    "her_log_n_ficheros": "   %d files in the output folder",
    "her_estado_exportado": "Exported: %s",
    "her_log_export_terminada": "Export finished in: %s",
    "her_log_comprobando_herr": "Checking external tools...",
    "her_disponible": "available: %s",
    "her_no_disponible": "NOT available",
    "her_err_no_completar": "Could not complete: %s",
    "her_motor_falta": "The extraction engine is missing (AssetStudioModCLI). Click «Update "
                       "libraries» in the extraction tab.",
    "her_err_bundle": "I can't find the bundle in the game: %s",
    "her_log_abriendo": "   opening %s ...",
    "her_err_sin_lista": "The engine didn't return the asset list.\n%s",
    "her_err_exportar": "The engine failed to export:\n%s",
    "her_err_wannacri": "I can't find wannacri (the .usm extractor). I don't install it on my "
                        "own: it's in the project's tools/wannacri. Without it the videos can't be "
                        "extracted.",
    "her_err_ffmpeg": "I can't find ffmpeg in the PATH. Without it the video can't be packed.",
    "her_log_wannacri": "   wannacri: %s",
    "her_err_sin_pista": "wannacri returned no video track. Output:\n%s",
    "her_log_ffmpeg": "   ffmpeg: %s -> %s",
    "her_err_ffmpeg_empaquetar": "ffmpeg failed to pack:\n%s",
    "her_log_video_listo": "   ready: %s (%.1f MB)",
    "her_log_audio_video": "   game sound: bank %s, track «%s»",
    "her_log_audio_video_mudo": "   game sound: bank %s, track «%s» — it is silence, delivering the muted video",
    "her_log_audio_video_no_hallado": "   no matched sound for %s (muted video)",
    "her_log_audio_video_varios": "   %d audio tracks in the MP4 (1st is the default): %s",
    "her_log_audio_video_repetida": "   bank %s: same track as %s, not duplicated",
    "her_idioma_ja": "Japanese",
    "her_idioma_zh": "Chinese",
    "her_idioma_base": "base",
    "her_pista_sfx": "effects (SFX)",
    "her_log_sin_cueinfo": "   I can't find CueInfoMap.txt: cannot match the sound",
    "her_log_hca": "   %d HCA track(s) found",
    "her_err_vgmstream": "I can't find vgmstream-cli (the HCA decoder). I don't install it on "
                         "my own: it's in the project's tools/vgmstream. Without it the audio "
                         "can't be decoded.",
    "her_log_wav": "   %s -> %s (%.1f MB)",
    "her_log_no_wav": "   could not decode %s",
    "her_err_sin_audio": "vgmstream decoded no track from the .awb.",
    "her_bundles_disco": "  —  listed from the game folder",
    "her_sync_construir": "Build index",
    "her_sync_cancelar": "Cancel",
    "her_sync_cancelando": "Cancelling the index...",
    "her_sync_cancelado": "Index cancelled: nothing was saved.",
    "her_sync_progreso": "Scanning bundle %d of %d...",
    "her_sync_empezando": "Preparing the scan...",
    "her_sync_confirmar": "The global search needs to scan the game's %d bundles with the engine. "
                          "It takes tens of minutes, but it's done only once: when it finishes it "
                          "is saved next to the program. You can cancel at any time. Start now?",
    "her_sync_aviso": "The global search doesn't have its index yet (%d bundles to scan). Build "
                      "it now? It takes tens of minutes and can be cancelled.",
    "her_sync_aviso_corto": "Search has no index yet (%d bundles to scan).",
    "her_sync_listo": "Index ready: %d resources across %d bundles.",
    "her_sync_parcial": "PARTIAL index: %d of %d bundles (%d resources). Build it again to search the whole game.",
    "her_sync_hecho": "Index built: %d resources.",
    "her_sync_guardado": "Index saved: %d resources in %s",
    "her_sync_reutilizado": " (%d bundles did not need to be read again: they hadn't changed)",
    "her_sync_sin_bundles": "I can't find any bundles: choose the game folder first.",
    "her_descargar_motor": "Download the engine",
    "her_deps_boton": "Download dependencies",
    "her_deps_titulo": "Downloading dependencies",
    "her_deps_peso": "The app is going to download the tools it needs (~%s MB in total). This window is view-only: you can't type in the console.",
    "her_deps_solo_ver": "Read-only console: you can watch the progress, you can't type in it.",
    "her_deps_cerrar": "Close",
    "her_deps_confirmar": "The external tools will be downloaded (about %s MB). Continue?",
    "her_deps_listo": "Done: the tools are in place.",
    "her_deps_fallo": "The rest downloaded, but something failed: %s",
    "her_deps_fuera": "Note: some copies live outside the folder (the app uses them, but they don't travel with it): %s",
    "her_motor_ya": "The engine is already installed.",
    "her_motor_confirmar": "The inspector and the exports need the extraction engine "
                           "(AssetStudioModCLI, about 16 MB). It is downloaded from its official "
                           "GitHub page and saved next to the program. Download it now?",
    "her_motor_listo": "Engine ready: %s",

    # ---------------------------------------------------------------- tools-only window
    "tools_lema": "Bundles, textures and video/audio from the game, without the model section.",
    "tools_juego": "Game:",
    "tools_elegir_juego": "Choose the game folder...",
    "tools_sin_juego": "not found (choose the game folder)",
    "tools_carpeta_guardada": "Game folder saved: %s\n%d bundles found.",
    "tools_carpeta_no_valida": "That folder isn't the game's. I look for `Client/OuterPackage/"
                               "Bundles/Windows` inside it.",
    "tools_log_titulo": "Activity",
    "tools_herramientas_solo": "P5X Studio Tools",

    # ---------------------------------------------------------------- dependencias
    "dep_progreso_cmd": "> %s ...",
    "dep_creando_uv": "Creating the environment with uv...",
    "dep_uv_fallo": "   uv failed, trying the system Python",
    "dep_creando_sistema": "Creating the environment with the system Python...",
    "dep_err_entorno": "Could not create the environment: %s",
    "dep_err_python": "The environment was created but I can't find its python.",
    "dep_librerias_dentro": "The libraries are bundled inside the tool.",
    "dep_instalando": "Installing what's missing: %s",
    "dep_err_instalar": "Could not install the libraries:\n%s",
    "dep_instaladas": "Installed.",
    "dep_descargando_motor": "Downloading the extraction engine...",
    "dep_descargando_pct": "   downloading: %d%%",
    "dep_descomprimiendo": "Unzipping...",
    "dep_err_descargar": "Could not download the extraction engine (no connection or GitHub "
                         "isn't responding).",
    "dep_err_motor_exe": "The engine was downloaded but I can't find the executable inside.",
    "dep_motor_listo": "Engine ready (%s).",
    "dep_version_desconocida": "unknown version",
    "dep_no_ejecutable": "executable not found",
    "dep_tardo": "took too long",
    "dep_sin_instalar": "(not installed)",
    "dep_sin_instalar2": "not installed",
    "dep_nueva": "   %s: %s -> %s",
    "dep_err_actualizar": "Could not update:\n%s",
    "dep_req_unitypy": "read the game's files",
    "dep_req_pillow": "generate the model previews",

    # ---------------------------------------------------------------- sesion de Unity
    "su_err_hub": "I couldn't open Unity Hub: %s",
    "su_msg_hub": "I've opened Unity Hub.\n\nSign in with your account (Unity Personal is "
                  "free) and, if it asks, activate the licence for version %s.\n\n"
                  "When you're done, click Check again: the licence is saved and batch mode "
                  "will work without asking you anything else.",
    "su_msg_sin_hub": "I can't find either Unity Hub or the Unity editor.\n\n"
                      "The editor is installed on this machine, but Hub, which is what activates "
                      "the licence, isn't. If you don't want to install it, open the editor by "
                      "hand once and activate the licence from there.",
    "su_err_unity": "I couldn't open Unity: %s",
    "su_msg_editor": "I can't find Unity Hub, so I opened the editor directly.\n\n"
                     "If the editor doesn't offer to sign you in, install Unity Hub: it's the "
                     "normal way to activate Unity Personal.\n\n"
                     "Once you have it, click Check again.",

    # ---------------------------------------------------------------- indice
    "ind_err_carpeta": "The game's bundles folder can't be found.",
    "ind_lista_oficial": "Reading the official bundle list...",
    "ind_recorriendo": "Scanning the downloaded files...",
    "ind_mapa": "Building the name map...",
    "ind_n_bundles": "   %d bundles in the manifest",
    "ind_n_ficheros": "   %d files on disk",
    "ind_n_nombres": "   %d logical names",
    "ind_guardado": "Index saved to %s",
    "ind_reconstruye": "The game changed since the last index: rebuilding.",

    # ---------------------------------------------------------------- unity (modo lote)
    "un_copiando": "Copying the capturer into the project...",
    "un_arrancando": "Starting Unity in batch mode (the first time takes a couple of minutes)...",
    "un_err_no_editor": "I can't find the Unity Editor on this machine",
    "un_err_capturador": "I can't find the capturer %s inside the tool",
    "un_err_proyecto": "the Unity project isn't valid: %s",
    "un_err_compila": "The Unity project doesn't compile. The failing scripts must be "
                      "neutralised (the game's come as AssetRipper stubs).",
    "un_revisa_log": "Check Unity's log: %s",
    "un_volcado_listo": "Dump ready: %d parts, %d with weights, %d unique bones.",
    "un_err_volcado": "Unity didn't dump the skeleton (code %d). %s",
    "un_err_malla": "Unity didn't assemble any mesh for character %s (does its prefab exist "
                    "in the project?). Log: %s",

    # ---------------------------------------------------------------- glb_rig
    "gr_err_sin_esqueleto_json": "the dump has no esqueleto.json: was it made by the Unity capturer?",
    "gr_err_sin_malla": "the dump has no mesh",
    "gr_err_sin_hueso": "no bone was learned: check the dump",
    "gr_huesos_mundo": "   bones with exact world (inverse bind): %d",
    "gr_nodos": "   bone nodes: %d",
    "gr_huesos_cizalla": "   bones re-parented to the root (local matrix had shear): %d",
    "gr_huesos_espejo": "   mirrored bones straightened (bind matrix with negative determinant): %d",
    "gr_glb_escrito": "3. GLB written: %s (%.2f MB)  bones %d  meshes %d  with weights %d  armatures %d",
    "gr_ajuste": "   prefab->reference fit: median residual %.4f m  worst %.4f m",
    "gr_parte": "   %-22s verts %6d  bones %4d  submeshes %d  expressions %d",
    "gr_aviso_huesos": "   warning %s: %d bones of the part without equivalent",
    "gr_material_heredado": "   inherited material for %s: %s",

    # ---------------------------------------------------------------- fbx_blender
    "fb_args": "missing arguments: -- [--glb <glb>] [--obj <folder>]... <output.fbx>",
    "fb_falta_salida": "the output FBX path is missing",
    "fb_armaduras": "[fbx] armatures %d  bones %d  meshes %d  with vertex groups %d",
    "fb_no_hay": "there is no GLB or OBJ to import",
    "fb_sin_glb": "[fbx] no GLB: importing %d OBJ parts (the FBX will come out without a skeleton)",
    "fb_no_importo": "no part was imported",
    "fb_exportado_obj": "[fbx] exported from OBJ (no skeleton): %s",
    "fb_importando_glb": "[fbx] importing the rigged GLB: %s",
    "fb_glb_sin_malla": "the GLB brought no mesh",
    "fb_exportado_glb": "[fbx] exported from the GLB: %s",
    "fb_no_importar": "[fbx] could not import %s (%s)",

    # ---------------------------------------------------------------- clave
    "cl_err_metadata": "I can't find global-metadata.dat in the game installation.\n"
                       "Without it the bundles can't be decrypted.",
    "cl_calculando": "Computing the decryption key (it can take a few minutes, only the "
                     "first time)...",
    "cl_obtenida": "Key obtained.",
    "cl_cache": "Decryption key recovered from cache.",

    # ---------------------------------------------------------------- catalogo
    "ct_skin": "   (skin: no face of its own)",
    "ct_escenario": "Scene",
    "ct_objeto": "Object",
    "ct_efecto": "Effect",
    "ct_personaje": "Character",

    # ---------------------------------------------------------------- nombres de traje
    "tr_normal": "Normal clothes",
    "tr_thief": "Thief outfit",
    "tr_uniform": "Uniform",
    "tr_uniform_swimsuit": "Swimsuit (uniform base)",
    "tr_thief_swimsuit": "Swimsuit (thief base)",
    "tr_swimsuit": "Swimsuit",
    "tr_dress": "Dress",
    "tr_catbag": "Cat costume",
    "tr_autumn": "Autumn clothes",
    "tr_office": "Office clothes",
    "tr_sports": "Sportswear",
    "tr_maidsuit": "Maid outfit",
    "tr_binghaofu": "Hospital gown",
    "tr_wheelchair": "Wheelchair",
    "tr_gamer": "Gamer clothes",
    "tr_doctor": "Doctor's coat",
    "tr_student": "School uniform",
    "tr_velvet": "Velvet",
    "tr_heize": "Black clothes",
    "tr_weiqun": "Skirt",
    "tr_manwu": "Dance outfit",
    "tr_chushifu": "Kitchen coat",
    "tr_kokatsu": "School uniform",
    "tr_unreal": "Unreal variant",
    "tr_sp": "SP variant",

    # ---------------------------------------------------------------- extractor
    "ex_falta_motor": "The extraction engine is missing. Click «Update libraries» in the "
                      "main window to download it.",
    "ex_motor_fallo": "The extraction engine failed:\n%s",
    "ex_motor_ficheros": "   engine: %d input files processed",
    "ex_progreso_fichero": "   (%d/%d) %s",
    "ex_no_procesar": "      this file could not be processed: %s",
    "ex_sin_bundles": "I can't find the game's bundles folder.",
    "ex_base_sin_ficheros": "I can't find any file of base model %s",
    "ex_base_sin_cara": "base model %s brings no usable face or eyes",
    "ex_base_tomadas": "Base model %s: %d files (group %s).",
    "ex_sin_ficheros": "I can't find any file of the character on disk.",
    "ex_traje_elegido": "Outfit chosen: %s (%s).",
    "ex_vive_en": "The character lives in %d files of the game.",
    "ex_extrayendo_de": "Extracting %s from %d files (it can take a few minutes)...",
    "ex_motor_devolvio": "The engine returned %d meshes and %d textures.",
    "ex_escenario_mallas": "Scene with %d meshes: the %d largest are drawn.",
    "ex_no_dibujar": "   could not draw %s (%s)",
    "ex_no_blender": "I can't find Blender, so I can't join the parts into an FBX. "
                     "The OBJ files are complete and open just the same.",
    "ex_blender_glb": "Blender is building the FBX from the rigged GLB (with skeleton)...",
    "ex_blender_obj": "There is no rigged GLB: Blender builds the FBX from the OBJ files "
                      "(it will come out WITHOUT a skeleton, because OBJ files carry no bones).",
    "ex_fbx_listo": "FBX ready: %s (%.1f MB%s)",
    "ex_con_esqueleto": ", with skeleton",
    "ex_sin_esqueleto": ", without skeleton",
    "ex_blender_no_escribio": "Blender didn't write the FBX: %s",
    "ex_no_fbx": "Could not create the FBX (%s). The OBJ files are complete.",
    "ex_esqueleto_respaldo_unity": "Reading the bundles directly was not enough; trying to build "
                                   "the skeleton inside Unity...",
    "ex_aviso_rig_bundles": "WARNING: could not read the skeleton from the bundles (%s).",
    "ru_manifiestos": "Rig manifests found: %d.",
    "ru_jerarquia": "Actor hierarchy: %d nodes.",
    "ru_parte": "Part %s: %d vertices, %d bones.",
    "ru_sin_manifiesto": "No bone manifest for %s; skipping.",
    "ex_esqueleto_listo": "Skeleton and weights ready: %d bones and %d of %d meshes with "
                          "vertex groups (%s).",
    "ex_skin_tomado": "This character is a skin: face, eyes and hair were taken from base "
                      "model %s (folder %s/). The body and clothes are its own.",
    "ex_aviso_sin_cara": "WARNING: this character has no face or eyes.",
    "ex_aviso_skin": "It usually means it's a SKIN: its face is in the base model, which is "
                     "other bundles. The body, hair, weapons and textures it does have are "
                     "complete.",
    "ex_aviso_indicar_base": "Set this character's base model (base search in the interface) "
                             "and the tool will bring its face, eyes and hair.",
    "ex_aviso_esqueleto_unity": "WARNING: could not get the skeleton with Unity (%s). The rest "
                                "of the model is complete.",
    "ex_aviso_glb": "WARNING: Unity dumped the data but the GLB could not be assembled (%s).",
    "ex_aviso_base": "WARNING: could not fetch base model %s (%s).",
    "ex_sin_unity_editor": "No Unity Editor installed: the model is delivered with geometry, "
                           "textures and materials, but without a skeleton or skin weights.",
    "ex_sin_proyecto_unity": "I can't find the decompiled Unity project (needed to get the "
                             "skeleton). You can set it in the tool's configuration, under "
                             "the key «proyecto_unity».",
    "ex_ensamblando_glb": "Assembling the GLB with the skeleton...",
    "ex_localizando": "Locating the character's files...",
    "ex_geometria": "Extracting geometry and textures...",
    "ex_ordenando": "Sorting what was extracted...",
    "ex_trayendo_base": "Fetching the face, eyes and hair from the base model...",
    "ex_esqueleto": "Getting the skeleton and skin weights...",
    "ex_rigs": "Getting the rigs from the game...",
    "ex_tabla": "Preparing the texture table...",
    "ex_previas": "Drawing the previews...",
    "ex_fbx": "Creating the final FBX...",
    "ex_escribiendo": "Writing the summary...",
    "ex_terminado": "Finished.",
    "ex_listo_en": "Done in %.1f seconds.",
    "ex_mapa_extra": "# extra map from the game: %s",
    "ex_base_parte_linea": "%s (%d meshes)",
    "ex_leeme_base":
        "# Parts taken from the base model\n\n"
        "This character is a SKIN: the game gives it no face. The face, the eyes (with eyelids) and\n"
        "the hair were taken from base model **%s**.\n\n"
        "- Base: `%s` (group: %s)\n"
        "- Parts taken: %s\n"
        "- Source bundles: %s\n\n"
        "The body, clothes and weapons in `01_model/` and `02_textures/` belong to the skin; what's\n"
        "in this folder comes from the base.\n",
    "prev_titulo": "%s - %s",
    "prev_titulo_lamina": "%s (%s)",
    "prev_titulo_base": "%s (base model) - %s",
    "prev_lamina_base": "%s - face, eyes and hair from base %s",
    "ex_rigs_sueltos": "Loose rigs exported: %d.",
    "ex_no_rigs": "The loose rigs could not be extracted (%s).",
    "ex_rigs_dentro": "This character brings no separate rigs: the bones go inside the OBJ "
                      "files themselves.",
    "ex_del_base": "From the base: %d meshes and %d textures of face, eyes and hair.",

    # extractor: nombres de parte
    "ex_parte_body": "Body and clothes",
    "ex_parte_face": "Face",
    "ex_parte_hair": "Hair",
    "ex_parte_eyes": "Eyes",
    "ex_parte_weapons": "Weapons",
    "ex_parte_other": "Other",

    # extractor: ficheros que escribe
    "ex_leeme": "The game's facial expressions are morphs (mesh shapes) and the OBJ format cannot\n"
                "store them. They are kept if the mesh is exported to FBX or opened in Unity.\n"
                "The face parts that were extracted are in 01_model/obj/face/.\n",
    "ex_tabla_titulo": "# Parts and textures",
    "ex_tabla_cab": "| mesh | origin | material | textures |",
    "ex_readme_intro": "Model extracted from the game with P5X Studio %s on %s.",
    "ex_readme_traje": "**Outfit:** %s (`%s`). This model brings ONLY this outfit of the character.",
    "ex_readme_tipo": "**Type:** %s. It's a game bundle turned into an extractable entry: it "
                      "brings its own meshes and textures. It's not a character, so it has no "
                      "face, skeleton or base model.",
    "ex_readme_previas_lim": "**Previews:** the scene has %d meshes; the %d largest were drawn. "
                             "The rest are equally in `01_model/obj/`.",
    "ex_readme_que_hay": "## What's inside",
    "ex_readme_carpeta_cont": "| folder | content |",
    "ex_readme_glb_row": "| `<name>.glb` | **THE MODEL**: mesh, UVs, embedded textures, skeleton "
                         "and skin weights in a single file. This is the one to open |",
    "ex_readme_fbx_all": "| `<name>_full.fbx` | the same model in FBX, with armature and weights, "
                         "in case your program prefers FBX |",
    "ex_readme_01": "| `01_model/obj/` | the loose geometry in OBJ, one file per part (geometry "
                    "and UVs only: no bones or weights) |",
    "ex_readme_02": "| `02_textures/` | the textures in PNG, the same ones embedded in the GLB |",
    "ex_readme_03": "| `03_skeleton/` | skeleton detail and counts (`esqueleto.json`) |",
    "ex_readme_04": "| `04_expressions/` | note about expressions (see LEEME.txt) |",
    "ex_readme_05": "| `05_materials/` | which texture each part uses |",
    "ex_readme_prev": "| `preview/` | previews (start with `lamina_completa.png`) |",
    "ex_readme_weapons": "| `01_model/obj/weapons/<weapon>/` | each weapon in its folder, with "
                         "its textures in `02_textures/weapons/<weapon>/` |",
    "ex_readme_other": "| `01_model/obj/other/<prop>/` | each prop in its folder, with its "
                       "textures in `02_textures/other/<prop>/` |",
    "ex_readme_base_row": "| `%s/` | face, eyes and hair taken from base model %s |",
    "ex_readme_fbx_rig": "| | the FBX carries the armature and skin weights, just like the GLB |",
    "ex_readme_fbx_norig": "| | the FBX was built from the OBJ files and therefore carries NO skeleton |",
    "ex_readme_piezas": "## Parts found",
    "ex_readme_parte_cab": "| part | meshes | textures |",
    "ex_readme_base_titulo": "## Base model",
    "ex_readme_base_1": "This character is a SKIN: the game gives it no face. The face, the eyes (with",
    "ex_readme_base_2": "eyelids) and the hair were taken from base model **%s** and are in the folder",
    "ex_readme_base_3": "`%s/`, separate from what the skin brings. Base bundles:",
    "ex_readme_base_parte": "- %s from the base: %d meshes, %d textures",
    "ex_readme_abrir": "## How to open it",
    "ex_readme_abrir_txt": "Open the `<name>.glb` in this folder: in Blender (File > Import > "
                           "glTF 2.0) or in any model viewer. It carries the mesh, the UVs, the "
                           "textures, the skeleton and the weights, so it shows up assembled and "
                           "with its colours without touching anything else. The FBX is the same "
                           "model in case your program prefers that format; the OBJ files in "
                           "`01_model/obj/` are just the loose geometry (no bones) for spot edits.",
    "ex_readme_lod": "Parts whose name ends in `_lod` or `_shadow` are low-quality or auxiliary "
                     "copies from the game: you can ignore them.",
    "ex_readme_armas_props": "Each weapon and each prop is in its own folder inside "
                             "`01_model/obj/`, and its MTL points only to that part's textures, "
                             "kept beside it in `02_textures/`: that way a weapon's textures "
                             "don't get mixed with the body's.",
    "ex_readme_esq_titulo": "## Skeleton and skin weights",
    "ex_readme_esq_1": "The rigged model is `<name>.glb`, in the root of this folder, and opens "
                       "directly in Blender or any glTF viewer, with its armature and skin weights.",
    "ex_readme_huesos": "- bones: %d",
    "ex_readme_pesos": "- meshes with weights: %d of %d",
    "ex_readme_morphs": "- facial expressions (morphs): %d",
    "ex_readme_hecho_unity": "- made with Unity %s (batch mode) on the game's decompiled project",
    "ex_readme_fbx_rig2": "The FBX `<name>_full.fbx` carries that same armature and those same "
                          "weights: it opens in Blender with its skeleton already assembled.",
    "ex_readme_esq_2": "The bones and the weights are read from the game's own bundles (the mesh "
                       "carries the skin and the inverse bind matrices; the actor's prefab, the "
                       "hierarchy; and the rig manifest, the bone order per mesh). Unity is not "
                       "needed.",
    "ex_readme_hecho_bundles": "- read from the game's bundles (no Unity)",
    "ex_readme_aviso": "## Notice",
    "ex_readme_aviso_txt": "Material extracted from the game for personal and research use. "
                           "Do not redistribute the original assets.",
    "ex_readme_tipo_escenario": "game scene",
    "ex_readme_tipo_objeto": "game object or prop",
    "ex_readme_tipo_efecto": "game effect",
    "ex_readme_tipo_modelo": "game model",
    # ---------------------------------------------------------------- bulk textures
    "web_bulk_tab": "Bulk textures",
    "web_bulk_titulo": "Bulk textures",
    "web_bulk_ayuda": "Pulls the textures out of EVERY bundle in the game and sorts them into folders "
                      "by category. Each texture ends up in Category/asset-set, where the asset set "
                      "is the bundle it comes from.",
    "web_bulk_col_categoria": "Category",
    "web_bulk_col_bundles": "Bundles",
    "web_bulk_col_texturas": "Textures",
    "web_bulk_col_peso": "Approx. size",
    "web_bulk_filtro": "Text filter",
    "web_bulk_filtro_ayuda": "Only extract textures whose name contains this (e.g. PC079 for a "
                             "character, scn11 for a scene, item). Empty = everything.",
    "web_bulk_sprites": "Include UI sprites (cropped pieces of the atlases)",
    "web_bulk_por_tipo": "Separate by map type (Color / Normal / Emission / Lightmap...)",
    "web_bulk_destino": "Destination folder",
    "web_bulk_elegir": "Choose...",
    "web_bulk_libre": "%s free on that drive",
    "web_bulk_empezar": "Extract selected",
    "web_bulk_cancelar": "Cancel",
    "web_bulk_ya_hecho": "%s bundles already done in this destination: a new run continues from there.",
    "web_bulk_estimado": "Estimated: %s textures, ~%s MB.",
    "web_bulk_estimado_filtro": "With a filter the size can't be known beforehand.",
    "web_bulk_aviso": "It only starts when you press the button, and you can cancel and continue later.",
    "web_bulk_vacio": "Nothing extracted in this folder yet.",
    "web_bulk_abrir": "Open the folder",
    "web_bulk_reanudar": "Continue from what is already done (recommended)",
    "web_bulk_todo": "All",
    "web_bulk_nada": "None",
    "web_bulk_progreso": "%s / %s bundles",
    "web_bulk_consola": "What's happening",
    "bulk_log_pasada": "Exporting batch %s (%d bundles)...",
    "bulk_log_arranca": "Bulk textures: %d bundles. Categories: %s",
    "bulk_log_lote": "%s: %d/%d bundles, %d files in place",
    "bulk_log_fallo": "%s: failed -> %s",
    "bulk_log_fin": "Done: %d textures sorted into their folders.",
    "bulk_log_cancelado": "Cancelled at %d/%d bundles (what's done is remembered).",
    "bulk_err_motor": "The engine failed exporting the batch: %s",
    "bulk_err_sin_categoria": "No category is ticked.",
    "bulk_err_lote_vacio": "%s: could not prepare the batch (bundles not found).",
    "bulk_fin": "Done: %s textures.",
    "bulk_fin_cancelado": "Cancelled: %s textures.",
    "bulk_err_espacio": "No room: about %s MB are needed and %s MB are free.",
    "web_bust_tab": "Bust-ups",
    "web_bust_title": "Bust-up viewer",
    "web_bust_sub": "The dialogue portraits, assembled layer by layer from the textures you extracted.",
    "web_bust_ph": "search a character…",
    "web_bust_expression": "Expression",
    "web_bust_shader": "Shader",
    "web_bust_tinte": "Tint",
    "web_bust_export": "Export PNG",
    "web_bust_reveal": "Show in folder",
    "web_bust_working": "Assembling…",
    "web_bust_n": "%s bust-ups",
    "web_bust_none": "No textures found. Use Extract portraits (about 170 MB) or run the full texture bulk.",
    "web_bust_elegir": "Choose folder…",
    "web_bust_capas": "Layers",
    "web_bust_avisos": "Notes",
    "web_bust_exportado": "Saved to %s",
    "web_bust_medido": "position measured by comparing pixels (%s% differ)",
    "web_bust_sin_cuerpo": "This bust-up has no body layer in the textures folder.",
    "web_bust_no_fiable": "its own sheet: position guessed",
        "web_bust_defecto": "Default",
                "web_bust_aviso_hoja": "Layers whose sheet is not the portrait canvas are left out (without the prefab there is no way to know where they go).",
                "web_bust_retr_titulo": "Portrait textures",
                "web_bust_retr_nota": "The viewer only needs the dialogue portraits: about 170 MB, instead of the bulk's 63 GB.",
                "web_bust_retr_boton": "Extract portraits",
                "web_bust_retr_parar": "Stop",
                "web_bust_retr_nada": "No portrait textures yet.",
                "web_bust_retr_listo": "Portraits ready: %s PNG · %s MB",
                "web_bust_retr_progreso": "Extracting portraits: %s/%s bundles",
                "web_bust_retr_fin": "%s PNG saved · %s MB",
                "web_bust_retr_bulk": "using the full bulk (%s)",
                "web_bust_retr_carpeta": "folder: %s",
                "retr_log_arranca": "Portraits: %s UI texture bundles",
                "retr_log_lote": "   portraits: %s/%s bundles · %s PNG kept",
    }