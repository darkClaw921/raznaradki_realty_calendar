#!/bin/bash

# Скрипт для тестирования webhook endpoints

BASE_URL="http://localhost:4001"

echo "🧪 Тестирование webhook endpoints..."
echo ""

# Проверка health endpoint
echo "1️⃣ Проверка health check..."
curl -s "${BASE_URL}/health" | jq .
echo ""

# Тест создания бронирования
# if [ -f "create_booking.json" ]; then
#     echo "2️⃣ Тест создания бронирования..."
#     curl -X POST "${BASE_URL}/webhook" \
#          -H "Content-Type: application/json" \
#          -d "$(jq -c '.[0].body' create_booking.json)" | jq .
#     echo ""
# else
#     echo "⚠️  Файл create_booking.json не найден"
# fi

# # Тест обновления бронирования
# if [ -f "update_booking.json" ]; then
#     echo "3️⃣ Тест обновления бронирования..."
#     curl -X POST "${BASE_URL}/webhook" \
#          -H "Content-Type: application/json" \
#          -d "$(jq -c '.[0].body' update_booking.json)" | jq .
#     echo ""
# else
#     echo "⚠️  Файл update_booking.json не найден"
# fi
# # Тест обновления бронирования с дуплексом
if [ -f "create_booking_duble.json" ]; then
    echo "3️⃣ Тест обновления бронирования..."
    curl -X POST "${BASE_URL}/webhook" \
         -H "Content-Type: application/json" \
         -d "$(jq -c '.[0].body' create_booking_duble.json)" | jq .
    echo ""
else
    echo "⚠️  Файл update_booking.json не найден"
fi

# Тест обновления бронирования с налогом
if [ -f "update_booking_tax.json" ]; then
    echo "4 Тест обновления бронирования с налогом..."
    curl -X POST "${BASE_URL}/webhook" \
         -H "Content-Type: application/json" \
         -d "$(jq -c '.[0].body' update_booking_tax.json)" | jq .
    echo ""
else
    echo "Файл update_booking_tax.json не найден"
fi

# Тест удаления бронирования
# if [ -f "delete_booking.json" ]; then
#     echo "4️⃣ Тест удаления бронирования..."
#     curl -X POST "${BASE_URL}/webhook" \
#          -H "Content-Type: application/json" \
#          -d "$(jq -c '.[0].body' delete_booking.json)" | jq .
#     echo ""
# else
#     echo "⚠️  Файл delete_booking.json не найден"
# fi

echo "✅ Тестирование завершено!"
echo ""
echo "🌐 Веб-интерфейс: ${BASE_URL}"
echo "📚 API документация: ${BASE_URL}/docs"

