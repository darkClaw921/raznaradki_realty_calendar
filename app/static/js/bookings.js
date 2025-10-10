/**
 * Скрипт для управления бронированиями
 * - Изменение размера столбцов с сохранением в localStorage
 * - Управление дополнительными услугами
 * - Редактирование комментариев
 */


// Константы
const STORAGE_KEY = 'bookings_table_column_widths';
const DEFAULT_COLUMN_WIDTHS = {
    0: 97,   // Адрес
    1: 100,  // Статус дома
    2: 90,   // ФИО (выс)
    3: 152,  // Телефон (выс)
    4: 167,  // Комментарий (выс)
    5: 99,   // ФИО (зас)
    6: 120,  // Телефон (зас)
    7: 100,  // Дата выселения
    8: 100,  // Кол-во дней
    9: 100,  // Общая сумма
    10: 111, // Предоплата
    11: 83,  // Доплата
    12: 77,  // Доп. услуги
    13: 141, // Комментарий (зас)
    14: 146  // Комментарии по оплате и проживанию
};
const COLUMN_COUNT = 15; // Количество столбцов во второй строке заголовков

// Глобальные переменные
let currentBookingId = null;
let availableServices = [];

/**
 * Форматирование числа с разделителем тысяч
 */
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return Math.round(num).toLocaleString('en-US').replace(/,/g, ',');
}

/**
 * Показать уведомление
 */
function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(notification);
    
    // Автоматически скрываем через 3 секунды
    setTimeout(function() {
        notification.remove();
    }, 3000);
}

/**
 * Получить ширину столбцов из localStorage
 */
function getColumnWidths() {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
        return JSON.parse(saved);
    }
    // Возвращаем дефолтные значения
    return { ...DEFAULT_COLUMN_WIDTHS };
}

/**
 * Сохранить ширину столбцов в localStorage
 */
function saveColumnWidths(widths) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(widths));
}

/**
 * Применить ширину столбцов к таблице
 */
function applyColumnWidths() {
    const widths = getColumnWidths();
    const table = document.querySelector('.table');
    if (!table) return;
    
    const headerRow = table.querySelector('thead tr:nth-child(2)');
    if (!headerRow) return;
    
    const headers = headerRow.querySelectorAll('th');
    let totalWidth = 0;
    
    headers.forEach((th, index) => {
        if (widths[index] !== undefined) {
            th.style.width = widths[index] + 'px';
            th.style.minWidth = widths[index] + 'px';
            th.style.maxWidth = widths[index] + 'px';
            totalWidth += widths[index];
        }
    });
    
    // Устанавливаем ширину таблицы равной сумме всех столбцов
    table.style.width = totalWidth + 'px';
}

/**
 * Обновить ширину таблицы на основе суммы ширин столбцов
 */
function updateTableWidth() {
    const table = document.querySelector('.table');
    if (!table) return;
    
    const headerRow = table.querySelector('thead tr:nth-child(2)');
    if (!headerRow) return;
    
    const headers = headerRow.querySelectorAll('th');
    let totalWidth = 0;
    
    headers.forEach((th) => {
        totalWidth += th.offsetWidth;
    });
    
    table.style.width = totalWidth + 'px';
}

/**
 * Инициализация изменения размера столбцов
 */
function initColumnResize() {
    const table = document.querySelector('.table');
    if (!table) return;
    
    const headerRow = table.querySelector('thead tr:nth-child(2)');
    if (!headerRow) return;
    
    const headers = headerRow.querySelectorAll('th');
    
    headers.forEach((th, index) => {
        // Создаем ресайзер
        const resizer = document.createElement('div');
        resizer.className = 'column-resizer';
        resizer.style.cssText = `
            position: absolute;
            top: 0;
            right: 0;
            width: 5px;
            height: 100%;
            cursor: col-resize;
            user-select: none;
            z-index: 1;
        `;
        
        th.style.position = 'relative';
        th.appendChild(resizer);
        
        let startX = 0;
        let startWidth = 0;
        
        resizer.addEventListener('mousedown', function(e) {
            e.preventDefault();
            startX = e.pageX;
            startWidth = th.offsetWidth;
            
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
            
            // Добавляем класс для визуальной индикации
            resizer.style.background = '#0d6efd';
        });
        
        function onMouseMove(e) {
            const diff = e.pageX - startX;
            const newWidth = startWidth + diff;
            
            // Нет минимальной ширины согласно требованиям
            th.style.width = newWidth + 'px';
            th.style.minWidth = newWidth + 'px';
            th.style.maxWidth = newWidth + 'px';
            
            // Обновляем ширину таблицы в реальном времени
            updateTableWidth();
        }
        
        function onMouseUp() {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            
            // Убираем визуальную индикацию
            resizer.style.background = '';
            
            // Сохраняем новую ширину
            const widths = getColumnWidths();
            widths[index] = th.offsetWidth;
            saveColumnWidths(widths);
            
            // Пересчитываем общую ширину таблицы
            updateTableWidth();
        }
    });
}

/**
 * Инициализация редактирования комментариев
 */
function initCommentEditing() {
    const editableComments = document.querySelectorAll('.editable-comment');
    
    editableComments.forEach(function(container) {
        const textarea = container.querySelector('.comment-textarea');
        const saveBtn = container.querySelector('.save-comment-btn');
        const bookingId = container.getAttribute('data-booking-id');
        const originalValue = textarea.value;
        
        // Показываем кнопку при изменении
        textarea.addEventListener('input', function() {
            if (textarea.value !== originalValue) {
                saveBtn.style.display = 'inline-block';
            } else {
                saveBtn.style.display = 'none';
            }
        });
        
        // Сохранение комментария
        saveBtn.addEventListener('click', function() {
            const comments = textarea.value;
            
            // Отправляем данные на сервер
            const formData = new FormData();
            formData.append('booking_id', bookingId);
            formData.append('comments', comments);
            
            fetch('/update-checkin-comment', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // Скрываем кнопку
                    saveBtn.style.display = 'none';
                    // Обновляем исходное значение
                    textarea.setAttribute('data-original', comments);
                    // Показываем уведомление
                    showNotification('Комментарий успешно сохранен', 'success');
                } else {
                    showNotification('Ошибка при сохранении', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Ошибка при сохранении', 'danger');
            });
        });
    });
}

/**
 * Загрузка списка доступных услуг
 */
function loadAvailableServices() {
    fetch('/services')
        .then(response => response.json())
        .then(data => {
            availableServices = data.services;
            populateServiceSelect();
        })
        .catch(error => {
            console.error('Error loading services:', error);
        });
}

/**
 * Заполнение выпадающего списка услуг
 */
function populateServiceSelect() {
    const select = document.getElementById('serviceSelect');
    select.innerHTML = '<option value="">Выберите услугу...</option>';
    availableServices.forEach(service => {
        const option = document.createElement('option');
        option.value = service.id;
        option.textContent = service.name;
        select.appendChild(option);
    });
}

/**
 * Загрузка сумм услуг для всех бронирований
 */
function loadAllServicesTotal() {
    const servicesCells = document.querySelectorAll('.services-cell');
    servicesCells.forEach(function(cell) {
        const bookingId = cell.getAttribute('data-booking-id');
        fetch(`/booking-services/${bookingId}`)
            .then(response => response.json())
            .then(data => {
                const totalSpan = cell.querySelector('.total-amount');
                totalSpan.textContent = formatNumber(data.total);
            })
            .catch(error => {
                console.error('Error loading services total:', error);
            });
    });
}

/**
 * Загрузка услуг для popover
 */
function loadServicesForPopover(bookingId, element, popoverInstance) {
    fetch(`/booking-services/${bookingId}`)
        .then(response => response.json())
        .then(data => {
            let content = '';
            
            if (data.services.length === 0) {
                content = '<div style="color: #6c757d; font-style: italic;">Нет добавленных услуг</div>';
            } else {
                content = '<div>';
                data.services.forEach(service => {
                    content += `
                        <div class="service-item">
                            <span><strong>${service.service_name}</strong></span>
                            <span>${formatNumber(service.price)}</span>
                        </div>
                    `;
                });
                content += `
                    <div style="margin-top: 10px; padding-top: 10px; border-top: 2px solid #dee2e6;">
                        <strong>Итого: ${formatNumber(data.total)}</strong>
                    </div>
                `;
                content += '</div>';
            }
            
            // Обновляем содержимое popover
            const popoverTip = bootstrap.Popover.getInstance(element);
            if (popoverTip) {
                popoverTip.setContent({
                    '.popover-body': content
                });
            }
        })
        .catch(error => {
            console.error('Error loading services for popover:', error);
            const popoverTip = bootstrap.Popover.getInstance(element);
            if (popoverTip) {
                popoverTip.setContent({
                    '.popover-body': '<div style="color: red;">Ошибка загрузки</div>'
                });
            }
        });
}

/**
 * Открытие модального окна услуг
 */
function openServicesModal(bookingId) {
    console.log('Opening services modal for booking:', bookingId);
    const modalElement = document.getElementById('servicesModal');
    if (!modalElement) {
        console.error('Modal element not found!');
        showNotification('Ошибка: модальное окно не найдено', 'danger');
        return;
    }
    
    loadBookingServices(bookingId);
    const modal = new bootstrap.Modal(modalElement);
    modal.show();
}

/**
 * Загрузка услуг бронирования
 */
function loadBookingServices(bookingId) {
    fetch(`/booking-services/${bookingId}`)
        .then(response => response.json())
        .then(data => {
            displayServices(data.services);
            document.getElementById('servicesTotal').textContent = formatNumber(data.total);
        })
        .catch(error => {
            console.error('Error loading booking services:', error);
        });
}

/**
 * Отображение списка услуг
 */
function displayServices(services) {
    const listDiv = document.getElementById('servicesList');
    
    if (services.length === 0) {
        listDiv.innerHTML = '<p class="text-muted">Нет добавленных услуг</p>';
        return;
    }
    
    let html = '<div class="list-group">';
    services.forEach(service => {
        html += `
            <div class="list-group-item d-flex justify-content-between align-items-center">
                <div>
                    <strong>${service.service_name}</strong>
                    <span class="text-muted ms-2">${formatNumber(service.price)}</span>
                </div>
                <button class="btn btn-sm btn-danger" onclick="deleteService(${service.id})">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
    });
    html += '</div>';
    listDiv.innerHTML = html;
}

/**
 * Добавление услуги
 */
function addService(bookingId, serviceId, price) {
    const formData = new FormData();
    formData.append('booking_id', bookingId);
    formData.append('service_id', serviceId);
    formData.append('price', price);
    
    fetch('/booking-services', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification('Услуга добавлена', 'success');
            loadBookingServices(bookingId);
            updateServiceTotal(bookingId);
            // Очищаем форму
            document.getElementById('serviceSelect').value = '';
            document.getElementById('servicePrice').value = '';
        } else {
            showNotification('Ошибка при добавлении услуги', 'danger');
        }
    })
    .catch(error => {
        console.error('Error adding service:', error);
        showNotification('Ошибка при добавлении услуги', 'danger');
    });
}

/**
 * Удаление услуги (глобальная функция)
 */
window.deleteService = function(serviceId) {
    if (!confirm('Удалить эту услугу?')) {
        return;
    }
    
    fetch(`/booking-services/${serviceId}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showNotification('Услуга удалена', 'success');
            loadBookingServices(currentBookingId);
            updateServiceTotal(currentBookingId);
        } else {
            showNotification('Ошибка при удалении услуги', 'danger');
        }
    })
    .catch(error => {
        console.error('Error deleting service:', error);
        showNotification('Ошибка при удалении услуги', 'danger');
    });
}

/**
 * Обновление общей суммы услуг
 */
function updateServiceTotal(bookingId) {
    fetch(`/booking-services/${bookingId}`)
        .then(response => response.json())
        .then(data => {
            const cell = document.querySelector(`.services-cell[data-booking-id="${bookingId}"]`);
            if (cell) {
                const totalSpan = cell.querySelector('.total-amount');
                totalSpan.textContent = formatNumber(data.total);
            }
        })
        .catch(error => {
            console.error('Error updating service total:', error);
        });
}

/**
 * Инициализация обработчиков кликов по адресу
 */
function initAddressClickHandlers() {
    const addressCells = document.querySelectorAll('.address-cell');
    
    addressCells.forEach(function(cell) {
        const checkoutId = cell.getAttribute('data-checkout-id');
        const checkinId = cell.getAttribute('data-checkin-id');
        
        // Если нет ни одного ID, пропускаем
        if (!checkoutId && !checkinId) {
            return;
        }
        
        // Если только один ID - сразу открываем ссылку при клике
        if ((checkoutId && !checkinId) || (!checkoutId && checkinId)) {
            const bookingId = checkoutId || checkinId;
            cell.addEventListener('click', function(e) {
                e.preventDefault();
                window.open(`https://realtycalendar.ru/chessmate/event/${bookingId}`, '_blank');
            });
        }
        // Если оба ID есть - показываем popover с выбором
        else if (checkoutId && checkinId) {
            // Создаем контент popover с двумя ссылками
            const popoverContent = `
                <div style="min-width: 200px;">
                    <div style="margin-bottom: 10px;">
                        <strong>Выберите бронирование:</strong>
                    </div>
                    <div class="d-grid gap-2">
                        <a href="https://realtycalendar.ru/chessmate/event/${checkoutId}" 
                           target="_blank" 
                           class="btn btn-sm btn-info">
                            <i class="bi bi-box-arrow-up-right"></i> Выселение
                        </a>
                        <a href="https://realtycalendar.ru/chessmate/event/${checkinId}" 
                           target="_blank" 
                           class="btn btn-sm btn-success">
                            <i class="bi bi-box-arrow-up-right"></i> Заселение
                        </a>
                    </div>
                </div>
            `;
            
            // Инициализируем popover
            const popover = new bootstrap.Popover(cell, {
                trigger: 'click',
                html: true,
                placement: 'right',
                content: popoverContent,
                sanitize: false
            });
            
            // Закрываем popover при клике вне его
            document.addEventListener('click', function(e) {
                if (!cell.contains(e.target)) {
                    popover.hide();
                }
            });
        }
    });
}

/**
 * Инициализация обработчиков услуг
 */
function initServicesHandlers() {
    console.log('Initializing services functionality...');
    console.log('Bootstrap available:', typeof bootstrap !== 'undefined');
    
    // Обработка клика по ячейке с услугами
    const servicesCells = document.querySelectorAll('.services-cell');
    console.log('Found services cells:', servicesCells.length);
    
    servicesCells.forEach(function(cell) {
        const totalDiv = cell.querySelector('.services-total');
        if (totalDiv) {
            const bookingId = cell.getAttribute('data-booking-id');
            console.log('Adding click handler to cell with booking ID:', bookingId);
            
            // Инициализируем popover
            const popover = new bootstrap.Popover(totalDiv, {
                trigger: 'hover focus',
                html: true,
                placement: 'left',
                content: 'Загрузка...',
                sanitize: false
            });
            
            // При наведении загружаем и показываем список услуг
            totalDiv.addEventListener('mouseenter', function() {
                loadServicesForPopover(bookingId, totalDiv, popover);
            });
            
            // При клике открываем модальное окно
            totalDiv.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                // Скрываем popover при клике
                popover.hide();
                console.log('Services cell clicked for booking:', bookingId);
                currentBookingId = bookingId;
                openServicesModal(currentBookingId);
            });
        } else {
            console.warn('Total div not found in cell');
        }
    });
    
    // Загружаем список услуг при загрузке страницы
    loadAvailableServices();
    
    // Загружаем суммы услуг для всех бронирований
    loadAllServicesTotal();
    
    // Добавление услуги
    const addServiceBtn = document.getElementById('addServiceBtn');
    if (addServiceBtn) {
        addServiceBtn.addEventListener('click', function() {
            const serviceId = document.getElementById('serviceSelect').value;
            const price = document.getElementById('servicePrice').value;
            
            if (!serviceId || !price) {
                showNotification('Выберите услугу и укажите цену', 'warning');
                return;
            }
            
            addService(currentBookingId, serviceId, price);
        });
    }
}

/**
 * Сброс ширины столбцов к значениям по умолчанию
 */
function resetColumnWidths() {
    if (confirm('Сбросить ширину столбцов к стандартным значениям?')) {
        // Сохраняем дефолтные значения
        saveColumnWidths(DEFAULT_COLUMN_WIDTHS);
        
        // Применяем их
        applyColumnWidths();
        
        // Показываем уведомление
        showNotification('Ширина столбцов сброшена к стандартным значениям', 'success');
    }
}

/**
 * Главная функция инициализации
 */
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing bookings page...');
    
    // Применяем сохраненные ширины столбцов
    applyColumnWidths();
    
    // Инициализируем изменение размера столбцов
    initColumnResize();
    
    // Инициализируем редактирование комментариев
    initCommentEditing();
    
    // Инициализируем обработчики услуг
    initServicesHandlers();
    
    // Инициализируем обработчики кликов по адресу
    initAddressClickHandlers();
    
    // Обработчик кнопки сброса ширины столбцов
    const resetWidthsBtn = document.getElementById('resetColumnWidthsBtn');
    if (resetWidthsBtn) {
        resetWidthsBtn.addEventListener('click', resetColumnWidths);
    }
});

