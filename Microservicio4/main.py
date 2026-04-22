from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import httpx
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar logging para ver qué está pasando
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Obtener URLs de los otros microservicios desde variables de entorno
MS1_URL = os.getenv("MS1_URL", "http://ms1-usuarios:8000")
MS2_URL = os.getenv("MS2_URL", "http://ms2-peliculas:3000")
MS3_URL = os.getenv("MS3_URL", "http://ms3-foro:8080")

# Credenciales para autenticación en MS1 (desde variables de entorno)
MS1_EMAIL = os.getenv("MS1_EMAIL", "eladminps@gmail.com")
MS1_PASSWORD = os.getenv("MS1_PASSWORD", "elpapuproadmin")

# Tiempo máximo para esperar respuesta de otros servicios
TIMEOUT = 10

# Crear la aplicación FastAPI
app = FastAPI(
    title="Microservicio 4: Orquestador",
    description="Combina información de usuarios, películas y foros",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# Modelos para las respuestas

class PerfilCompleto(BaseModel):
    """Toda la información del usuario en un solo lugar"""
    usuario_id: int
    usuario_info: Optional[Dict[str, Any]] = None
    historial_peliculas: Optional[List[Dict[str, Any]]] = None
    grupos: Optional[List[Dict[str, Any]]] = None
    errores: List[str] = []

class EstadisticasUsuario(BaseModel):
    """Resumen de las películas vistas por el usuario"""
    usuario_id: int
    total_peliculas_vistas: int
    conteo_por_genero: Dict[str, int]
    genero_favorito: Optional[str] = None
    ultima_pelicula: Optional[str] = None

class HealthCheck(BaseModel):
    """Estado de salud del orquestador y sus dependencias"""
    status: str
    ms1_status: str
    ms2_status: str
    ms3_status: str
    timestamp: str

# Funciones auxiliares

def verificar_salud_microservicio(url: str, timeout: int = TIMEOUT) -> bool:
    """Intenta conectar a un microservicio para ver si está activo"""
    try:
        import httpx as sync_httpx
        
        # Determinar si es MS1 para usar autenticación
        usar_auth = (url == MS1_URL)
        auth = (MS1_EMAIL, MS1_PASSWORD) if usar_auth else None
        
        # Intentar primero con /health
        try:
            response = sync_httpx.get(f"{url}/health", timeout=timeout, auth=auth)
            if response.status_code == 200:
                return True
        except:
            pass
        
        # Si /health no existe o falla, intentar con /usuarios (MS1) o /api/movies (MS2)
        endpoints_alternos = ["/usuarios", "/api/movies", "/api/threads"]
        for endpoint in endpoints_alternos:
            try:
                response = sync_httpx.get(f"{url}{endpoint}", timeout=timeout, auth=auth)
                if response.status_code in [200, 404]:  # 200 = existe, 404 = al menos responde
                    return True
            except:
                continue
        
        return False
    except Exception as e:
        logger.warning(f"No se pudo conectar a {url}: {str(e)}")
        return False

async def obtener_usuario_ms1(usuario_id: int) -> Optional[Dict[str, Any]]:
    """Pide la info del usuario a MS1 con autenticación"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MS1_URL}/usuarios/{usuario_id}",
                auth=(MS1_EMAIL, MS1_PASSWORD),
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                return None
            else:
                logger.error(f"Error en MS1: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"No se pudo conectar a MS1: {str(e)}")
        return None

async def obtener_historial_ms1(usuario_id: int) -> Optional[Dict[str, Any]]:
    """Pide el historial de películas vistas a MS1 con autenticación"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MS1_URL}/usuarios/{usuario_id}/peliculas_vistas",
                auth=(MS1_EMAIL, MS1_PASSWORD),
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                peliculas = response.json()
                return {"peliculas_vistas": peliculas if isinstance(peliculas, list) else []}
            else:
                logger.warning(f"MS1 respondió con: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"No se pudo obtener historial de MS1: {str(e)}")
        return None

async def obtener_threads_ms3(usuario_id: int) -> Optional[List[Dict[str, Any]]]:
    """Obtiene los threads (como grupos/comunidades) disponibles en MS3
    Nota: MS3 no tiene endpoint específico por usuario, así que retorna todos los threads
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MS3_URL}/api/threads",
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else data.get("data", [])
            else:
                logger.warning(f"MS3 respondió con: {response.status_code}")
                return []
    except Exception as e:
        logger.error(f"No se pudo conectar a MS3: {str(e)}")
        return []

async def obtener_threads_creados_ms3(usuario_id: int) -> List[Dict[str, Any]]:
    """Obtiene threads creados por un usuario específico"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MS3_URL}/api/threads",
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                threads = data if isinstance(data, list) else data.get("data", [])
                
                # Filtrar threads del usuario (comparar como string)
                threads_usuario = []
                for t in threads:
                    if t and isinstance(t, dict):
                        user_id_thread = t.get("userId")
                        if user_id_thread and str(user_id_thread) == str(usuario_id):
                            threads_usuario.append(t)
                
                return threads_usuario
            return []
    except Exception as e:
        logger.error(f"Error obteniendo threads creados: {str(e)}")
        return []

async def obtener_posts_usuario_ms3(usuario_id: int) -> List[Dict[str, Any]]:
    """Obtiene posts creados por un usuario en MS3"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MS3_URL}/api/posts/all?page=0&size=1000",
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                # MS3 devuelve Page<Post>, extraer content
                if isinstance(data, dict):
                    posts = data.get("content", [])
                else:
                    posts = data if isinstance(data, list) else []
                
                # Filtrar posts del usuario (comparar como string)
                posts_usuario = []
                for p in posts:
                    if p and isinstance(p, dict):
                        user_id_post = p.get("userId")
                        if user_id_post and str(user_id_post) == str(usuario_id):
                            posts_usuario.append(p)
                
                return posts_usuario
            return []
    except Exception as e:
        logger.warning(f"No se pudo obtener posts del usuario: {str(e)}")
        return []

async def obtener_todas_peliculas_ms2() -> List[Dict[str, Any]]:
    """Obtiene todas las películas de MS2"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MS2_URL}/api/movies",
                timeout=TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else data.get("data", [])
            return []
    except Exception as e:
        logger.warning(f"Error obteniendo películas: {str(e)}")
        return []

# Endpoints de la API

@app.get("/", tags=["General"])
async def raiz():
    """Endpoint raíz para verificar que el servicio está corriendo"""
    return {
        "mensaje": "Microservicio Orquestador funcionando",
        "version": "1.0.0",
        "documentacion": "/docs"
    }

@app.get("/health", tags=["General"])
async def health_check() -> HealthCheck:
    """Verifica si el orquestador y todos los microservicios están activos"""
    ms1_ok = verificar_salud_microservicio(MS1_URL)
    ms2_ok = verificar_salud_microservicio(MS2_URL)
    ms3_ok = verificar_salud_microservicio(MS3_URL)
    
    estado_general = "healthy" if (ms1_ok and ms2_ok and ms3_ok) else "degraded"
    
    return HealthCheck(
        status=estado_general,
        ms1_status="healthy" if ms1_ok else "unhealthy",
        ms2_status="healthy" if ms2_ok else "unhealthy",
        ms3_status="healthy" if ms3_ok else "unhealthy",
        timestamp=datetime.now().isoformat()
    )

@app.get("/api/v1/users/{usuario_id}", 
         response_model=PerfilCompleto,
         tags=["Usuarios"],
         summary="Perfil completo del usuario")
async def obtener_perfil_completo(usuario_id: int) -> PerfilCompleto:
    """
    Trae toda la información del usuario de los tres microservicios:
    - Datos básicos de MS1
    - Películas vistas de MS2
    - Grupos en los que está de MS3
    
    Retorna los datos disponibles + lista de errores en caso de fallas parciales
    """
    errores = []
    
    # Obtener datos de los tres servicios
    usuario_info = await obtener_usuario_ms1(usuario_id)
    if usuario_info is None:
        errores.append("Usuario no encontrado en MS1 (404)")
    
    historial = await obtener_historial_ms1(usuario_id)
    if historial is None:
        errores.append("No se pudo obtener historial de MS1")
    
    threads = await obtener_threads_ms3(usuario_id)
    if not threads:
        errores.append("No hay threads disponibles en MS3")
    
    # Extraer lista de películas del historial si es un dict
    peliculas_lista = None
    if historial and isinstance(historial, dict):
        peliculas_lista = historial.get("peliculas_vistas", [])
    
    # Retornar respuesta con los datos disponibles
    # Si no hay usuario, igualmente retornar el objeto con None
    return PerfilCompleto(
        usuario_id=usuario_id,
        usuario_info=usuario_info,
        historial_peliculas=peliculas_lista,
        grupos=threads if threads else [],
        errores=errores
    )

@app.get("/api/v1/users/{usuario_id}/stats", 
         response_model=EstadisticasUsuario,
         tags=["Usuarios"],
         summary="Estadísticas del usuario")
async def obtener_estadisticas(usuario_id: int) -> EstadisticasUsuario:
    """
    Muestra un resumen de las películas que vio el usuario:
    - Cuántas películas vio en total
    - Cuáles géneros vio más
    - Cuál es su género favorito
    """
    # Obtener el historial de MS1
    historial = await obtener_historial_ms1(usuario_id)
    
    # Procesar datos reales del historial
    total_peliculas = 0
    conteo_genero = {}
    ultima_pelicula = None
    
    if historial and isinstance(historial, dict):
        peliculas = historial.get("peliculas_vistas", [])
        total_peliculas = len(peliculas)
        
        # Contar géneros si están disponibles
        for pelicula in peliculas:
            genero = pelicula.get("genero", "Desconocido")
            conteo_genero[genero] = conteo_genero.get(genero, 0) + 1
        
        # Obtener última película
        if peliculas:
            ultima_pelicula = peliculas[0].get("titulo", "Desconocida")
    
    # Si no hay datos, usar valores por defecto
    if not conteo_genero:
        conteo_genero = {"Acción": 0, "Drama": 0, "Comedia": 0}
    
    # Calcular género favorito (evitar error de tipo en max)
    genero_favorito = None
    if conteo_genero:
        genero_favorito = max(conteo_genero.items(), key=lambda x: x[1])[0]
    
    return EstadisticasUsuario(
        usuario_id=usuario_id,
        total_peliculas_vistas=total_peliculas,
        conteo_por_genero=conteo_genero,
        genero_favorito=genero_favorito,
        ultima_pelicula=ultima_pelicula
    )

@app.get("/api/v1/users/{usuario_id}/history",
         tags=["Usuarios"],
         summary="Historial de películas")
async def obtener_historial(usuario_id: int):
    """Retorna el historial de películas vistas por el usuario (desde MS1)"""
    historial = await obtener_historial_ms1(usuario_id)
    
    if historial is None:
        return {
            "usuario_id": usuario_id,
            "peliculas_vistas": [],
            "total": 0,
            "error": "No se pudo obtener el historial"
        }
    
    peliculas = historial.get("peliculas_vistas", [])
    return {
        "usuario_id": usuario_id,
        "peliculas_vistas": peliculas,
        "total": len(peliculas)
    }

@app.get("/api/v1/users/{usuario_id}/groups",
         tags=["Usuarios"],
         summary="Comunidades (threads) disponibles")
async def obtener_comunidades(usuario_id: int):
    """Retorna los threads (comunidades) disponibles en MS3
    Nota: MS3 no filtra por usuario específico, retorna todos los threads disponibles
    """
    threads = await obtener_threads_ms3(usuario_id)
    
    return {
        "usuario_id": usuario_id,
        "threads_disponibles": threads,
        "total": len(threads) if isinstance(threads, list) else 0
    }

@app.get("/api/v1/users/{usuario_id}/created-groups",
         tags=["Usuarios"],
         summary="Grupos creados por el usuario")
async def obtener_grupos_creados(usuario_id: int):
    """Retorna los threads/grupos creados por el usuario en MS3"""
    threads_creados = await obtener_threads_creados_ms3(usuario_id)
    
    return {
        "usuario_id": usuario_id,
        "grupos_creados": threads_creados,
        "total": len(threads_creados)
    }

@app.get("/api/v1/users/{usuario_id}/participated-groups",
         tags=["Usuarios"],
         summary="Grupos donde el usuario participó")
async def obtener_grupos_participados(usuario_id: int):
    """Retorna los threads donde el usuario ha escrito posts"""
    posts = await obtener_posts_usuario_ms3(usuario_id)
    
    # Extraer thread IDs únicos donde el usuario participó
    thread_ids = set()
    for post in posts:
        thread_id = post.get("threadId")
        if thread_id:
            thread_ids.add(thread_id)
    
    return {
        "usuario_id": usuario_id,
        "thread_ids_participados": list(thread_ids),
        "total": len(thread_ids)
    }

@app.get("/api/v1/users/{usuario_id}/top-genres",
         tags=["Análisis"],
         summary="Géneros más visto del usuario")
async def obtener_generos_top(usuario_id: int):
    """Retorna los géneros más vistos por el usuario ordenados por frecuencia"""
    historial = await obtener_historial_ms1(usuario_id)
    
    if not historial:
        return {
            "usuario_id": usuario_id,
            "generos": [],
            "error": "Sin historial"
        }
    
    peliculas = historial.get("peliculas_vistas", [])
    conteo = {}
    
    for pelicula in peliculas:
        genero = pelicula.get("genero", "Desconocido")
        conteo[genero] = conteo.get(genero, 0) + 1
    
    # Ordenar por cantidad (descendente)
    ordenado = sorted(conteo.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "usuario_id": usuario_id,
        "generos_ordenados": [{"genero": g, "cantidad": c} for g, c in ordenado]
    }

@app.get("/api/v1/movies/stats",
         tags=["Análisis"],
         summary="Estadísticas generales de películas")
async def obtener_stats_peliculas():
    """Retorna estadísticas generales de todas las películas
    - Géneros más populares
    - Actores más frecuentes
    - Directores más frecuentes
    """
    peliculas = await obtener_todas_peliculas_ms2()
    
    if not peliculas:
        return {
            "error": "No se pudieron obtener películas",
            "generos": {},
            "actores": {},
            "directores": {}
        }
    
    # Contar géneros (asumiendo estructura)
    conteo_generos = {}
    conteo_actores = {}
    conteo_directores = {}
    
    for pelicula in peliculas:
        # Géneros
        genero = pelicula.get("genre", "Desconocido")
        if genero:
            conteo_generos[genero] = conteo_generos.get(genero, 0) + 1
        
        # Actores (si es lista)
        actores = pelicula.get("actors", [])
        if isinstance(actores, list):
            for actor in actores:
                actor_name = actor.get("name") if isinstance(actor, dict) else str(actor)
                if actor_name:
                    conteo_actores[actor_name] = conteo_actores.get(actor_name, 0) + 1
        
        # Directores
        director = pelicula.get("director", "Desconocido")
        if director:
            conteo_directores[director] = conteo_directores.get(director, 0) + 1
    
    # Top 10 de cada uno
    top_generos = sorted(conteo_generos.items(), key=lambda x: x[1], reverse=True)[:10]
    top_actores = sorted(conteo_actores.items(), key=lambda x: x[1], reverse=True)[:10]
    top_directores = sorted(conteo_directores.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "total_peliculas": len(peliculas),
        "top_generos": [{"nombre": g, "cantidad": c} for g, c in top_generos],
        "top_actores": [{"nombre": a, "cantidad": c} for a, c in top_actores],
        "top_directores": [{"nombre": d, "cantidad": c} for d, c in top_directores]
    }
