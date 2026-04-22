#!/bin/bash

# Script para probar MS4 - Orquestador
BASE_URL="http://localhost:8004"
USER_ID=1

echo "=== Pruebas del Microservicio 4 (Orquestador) ==="
echo ""

echo "1. Health Check"
curl -X GET "$BASE_URL/health" | jq .
echo -e "\n"

echo "2. Raíz"
curl -X GET "$BASE_URL/" | jq .
echo -e "\n"

echo "3. Perfil Completo del Usuario $USER_ID"
curl -X GET "$BASE_URL/api/v1/users/$USER_ID" | jq .
echo -e "\n"

echo "4. Estadísticas del Usuario $USER_ID"
curl -X GET "$BASE_URL/api/v1/users/$USER_ID/stats" | jq .
echo -e "\n"

echo "5. Historial de Películas del Usuario $USER_ID"
curl -X GET "$BASE_URL/api/v1/users/$USER_ID/history" | jq .
echo -e "\n"

echo "6. Grupos del Usuario $USER_ID"
curl -X GET "$BASE_URL/api/v1/users/$USER_ID/groups" | jq .
echo -e "\n"

echo "7. Usuario que no existe (999999)"
curl -X GET "$BASE_URL/api/v1/users/999999" | jq .
echo -e "\n"

echo "=== Pruebas completadas ==="
