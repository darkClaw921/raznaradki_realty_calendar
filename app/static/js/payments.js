// JavaScript для страницы поступлений денег

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация
    initAddPaymentForm();
    initDeleteButtons();
    initCalculateAdvance();
    initBookingSelect();
    
    // Установить сегодняшнюю дату по умолчанию
    const receiptDateInput = document.getElementById('receipt_date');
    if (receiptDateInput && !receiptDateInput.value) {
        receiptDateInput.valueAsDate = new Date();
    }
});


/**
 * Инициализация выбора бронирования
 */
function initBookingSelect() {
    const bookingSelect = document.getElementById('booking_select');
    const bookingServiceSelect = document.getElementById('booking_service_select');
    const apartmentTitleInput = document.getElementById('apartment_title');
    const amountInput = document.getElementById('amount');
    const incomeCategoryInput = document.getElementById('income_category');
    
    if (!bookingSelect || !bookingServiceSelect) return;
    
    bookingSelect.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        
        if (!selectedOption.value) {
            // Очистить список услуг
            bookingServiceSelect.innerHTML = '<option value="">-- Сначала выберите бронирование --</option>';
            return;
        }
        
        // Получить данные бронирования
        const apartmentTitle = selectedOption.getAttribute('data-apartment');
        const servicesJson = selectedOption.getAttribute('data-services');
        
        // Заполнить объект
        if (apartmentTitle && apartmentTitleInput) {
            apartmentTitleInput.value = apartmentTitle;
        }
        
        // Заполнить список услуг
        try {
            const services = JSON.parse(servicesJson);
            bookingServiceSelect.innerHTML = '<option value="">-- Выберите услугу (опционально) --</option>';
            
            services.forEach(service => {
                const option = document.createElement('option');
                option.value = service.id;
                option.textContent = `${service.service_name} - ${formatNumber(service.price)}`;
                option.setAttribute('data-price', service.price);
                option.setAttribute('data-service-name', service.service_name);
                bookingServiceSelect.appendChild(option);
            });
        } catch (e) {
            console.error('Ошибка при парсинге услуг:', e);
            bookingServiceSelect.innerHTML = '<option value="">-- Нет услуг --</option>';
        }
    });
    
    // При выборе услуги - заполнить сумму и статью
    bookingServiceSelect.addEventListener('change', function() {
        const selectedOption = this.options[this.selectedIndex];
        
        if (selectedOption.value) {
            const price = selectedOption.getAttribute('data-price');
            const serviceName = selectedOption.getAttribute('data-service-name');
            
            if (price && amountInput) {
                amountInput.value = price;
            }
            
            if (serviceName && incomeCategoryInput) {
                incomeCategoryInput.value = serviceName;
            }
        }
    });
}


/**
 * Инициализация формы добавления поступления
 */
function initAddPaymentForm() {
    const form = document.getElementById('addPaymentForm');
    if (!form) return;
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        
        // Очистка пустых строк для опциональных числовых полей
        // Если поле пустое, удаляем его из formData (будет None на сервере)
        const numericFields = ['booking_id', 'booking_service_id', 'advance_for_future'];
        numericFields.forEach(field => {
            const value = formData.get(field);
            if (value === '' || value === null) {
                formData.delete(field);
            }
        });
        
        try {
            const response = await fetch('/payments/create', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                showNotification('Поступление успешно создано', 'success');
                
                // Закрыть модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('addPaymentModal'));
                modal.hide();
                
                // Перезагрузить страницу
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification('Ошибка: ' + data.message, 'danger');
            }
        } catch (error) {
            console.error('Ошибка при создании поступления:', error);
            showNotification('Ошибка при создании поступления', 'danger');
        }
    });
}


/**
 * Инициализация кнопок удаления
 */
function initDeleteButtons() {
    const deleteButtons = document.querySelectorAll('.delete-payment');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const paymentId = this.getAttribute('data-payment-id');
            
            if (!confirm('Вы уверены, что хотите удалить это поступление?')) {
                return;
            }
            
            try {
                const response = await fetch(`/payments/${paymentId}`, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    showNotification('Поступление удалено', 'success');
                    
                    // Удалить строку из таблицы
                    const row = document.querySelector(`tr[data-payment-id="${paymentId}"]`);
                    if (row) {
                        row.remove();
                    }
                    
                    // Проверить, есть ли еще записи
                    const tbody = document.getElementById('paymentsTableBody');
                    if (tbody && tbody.querySelectorAll('tr').length === 0) {
                        tbody.innerHTML = '<tr><td colspan="9" class="text-center">Нет данных для отображения</td></tr>';
                    }
                } else {
                    showNotification('Ошибка: ' + data.message, 'danger');
                }
            } catch (error) {
                console.error('Ошибка при удалении поступления:', error);
                showNotification('Ошибка при удалении поступления', 'danger');
            }
        });
    });
}


/**
 * Инициализация кнопки расчета аванса
 */
function initCalculateAdvance() {
    const calculateBtn = document.getElementById('calculateAdvanceBtn');
    if (!calculateBtn) return;
    
    calculateBtn.addEventListener('click', async function() {
        const apartmentTitle = document.getElementById('apartment_title').value;
        const receiptDate = document.getElementById('receipt_date').value;
        
        if (!apartmentTitle) {
            showNotification('Выберите объект', 'warning');
            return;
        }
        
        if (!receiptDate) {
            showNotification('Выберите дату поступления', 'warning');
            return;
        }
        
        try {
            const response = await fetch(`/payments/calculate-advance?apartment_title=${encodeURIComponent(apartmentTitle)}&selected_date=${receiptDate}`);
            
            const data = await response.json();
            
            if (data.status === 'success') {
                const advanceInput = document.getElementById('advance_for_future');
                advanceInput.value = data.total_advance.toFixed(2);
                
                if (data.total_advance > 0) {
                    showNotification(`Рассчитана сумма аванса: ${formatNumber(data.total_advance)}`, 'success');
                } else {
                    showNotification('Нет будущих заселений с предоплатой', 'info');
                }
            } else {
                showNotification('Ошибка: ' + data.message, 'danger');
            }
        } catch (error) {
            console.error('Ошибка при расчете аванса:', error);
            showNotification('Ошибка при расчете аванса', 'danger');
        }
    });
}


/**
 * Форматирование числа с разделителем тысяч
 */
function formatNumber(num) {
    return Number(num).toFixed(0).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}


/**
 * Показать уведомление
 */
function showNotification(message, type = 'info') {
    const container = document.getElementById('notificationContainer');
    if (!container) return;
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    container.appendChild(alertDiv);
    
    // Автоматически скрыть через 5 секунд
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => {
            alertDiv.remove();
        }, 150);
    }, 5000);
}
