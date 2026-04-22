# Microservicio 4 - Orquestador

## Descripción
Microservicio orquestador que combina información de los otros 3 microservicios:
- **MS1** (Usuarios): Perfil de usuario
- **MS2** (Películas): Catálogo de películas
- **MS3** (Foro): Comunidades y threads

**No tiene base de datos propia**, solo consulta a los otros microservicios y devuelve datos combinados.

---

## Requisitos
- Docker y Docker Compose
- Python 3.9+ (si ejecutas localmente)
- Los otros 3 repos: MS1, MS2, MS3

---

## Quick Start

### 1. Levantar TODO
```bash
docker-compose up -d
```

### 2. Generar datos de prueba
```bash
python seed_usuarios.py
```
Esto crea 5 usuarios en MS1.

### 3. Verificar que está corriendo
```bash
GET http://localhost:8004/health
```

---

## Cómo Probar en Postman

### Perfil Completo del Usuario
```
GET http://localhost:8004/api/v1/users/1
```
Devuelve: usuario, películas vistas, threads del foro

### Estadísticas del Usuario
```
GET http://localhost:8004/api/v1/users/1/stats
```
Devuelve: cantidad de películas, géneros favoritos

### Historial de Películas
```
GET http://localhost:8004/api/v1/users/1/history
```
Devuelve: lista de películas vistas

### Comunidades Disponibles
```
GET http://localhost:8004/api/v1/users/1/groups
```
Devuelve: threads disponibles en el foro

---

## Documentación Interactiva
- **Swagger UI**: http://localhost:8004/docs
- **ReDoc**: http://localhost:8004/redoc

---

## Ejecutar Localmente

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
uvicorn main:app --reload --port 8004
```

---

## Variables de Entorno
```
MS1_URL=http://ms1-usuarios:8000
MS2_URL=http://ms2-peliculas:3000
MS3_URL=http://ms3-foro:8080
TIMEOUT=10
```

---

## Endpoints Disponibles
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Raíz del servicio |
| GET | `/health` | Estado de MS4 y dependencias |
| GET | `/api/v1/users/{id}` | Perfil completo del usuario |
| GET | `/api/v1/users/{id}/stats` | Estadísticas del usuario |
| GET | `/api/v1/users/{id}/history` | Historial de películas |
| GET | `/api/v1/users/{id}/groups` | Comunidades disponibles |
| GET | `/api/v1/users/{id}/created-groups` | Grupos creados por el usuario |
| GET | `/api/v1/users/{id}/participated-groups` | Grupos donde participó |
| GET | `/api/v1/users/{id}/top-genres` | Géneros más vistos |
| GET | `/api/v1/movies/stats` | Estadísticas generales de películas |
