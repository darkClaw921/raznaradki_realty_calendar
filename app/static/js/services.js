/**
 * JavaScript для страницы управления услугами
 */

document.addEventListener('DOMContentLoaded', function() {
    initAddServiceForm();
    initEditServiceButtons();
    initToggleStatusButtons();
});

/**
 * Инициализация формы добавления услуги
 */
function initAddServiceForm() {
    const form = document.getElementById('addServiceForm');
    if (!form) return;

    form.addEventListener('submit', async function(e) {
        e.preventDefault();

        const formData = new FormData(form);
        const serviceName = formData.get('name').trim();

        if (!serviceName) {
            showNotification('Название услуги не может быть пустым', 'warning');
            return;
        }

        try {
            const response = await fetch('/services/create', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.status === 'success') {
                showNotification(data.message, 'success');
                
                // Закрываем модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('addServiceModal'));
                modal.hide();
                
                // Очищаем форму
                form.reset();
                
                // Перезагружаем страницу для обновления списка
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification(data.message || 'Ошибка при создании услуги', 'danger');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            showNotification('Ошибка при создании услуги', 'danger');
        }
    });
}

/**
 * Инициализация кнопок редактирования услуг
 */
function initEditServiceButtons() {
    const editButtons = document.querySelectorAll('.edit-service-btn');
    
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const serviceId = this.getAttribute('data-service-id');
            const serviceName = this.getAttribute('data-service-name');
            
            // Заполняем форму редактирования
            document.getElementById('editServiceId').value = serviceId;
            document.getElementById('editServiceName').value = serviceName;
            
            // Открываем модальное окно
            const modal = new bootstrap.Modal(document.getElementById('editServiceModal'));
            modal.show();
        });
    });
    
    // Инициализация формы редактирования
    const editForm = document.getElementById('editServiceForm');
    if (!editForm) return;
    
    editForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const serviceId = document.getElementById('editServiceId').value;
        const serviceName = document.getElementById('editServiceName').value.trim();
        
        if (!serviceName) {
            showNotification('Название услуги не может быть пустым', 'warning');
            return;
        }
        
        try {
            const formData = new FormData();
            formData.append('name', serviceName);
            
            const response = await fetch(`/services/${serviceId}`, {
                method: 'PUT',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                showNotification(data.message, 'success');
                
                // Закрываем модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('editServiceModal'));
                modal.hide();
                
                // Перезагружаем страницу для обновления списка
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification(data.message || 'Ошибка при обновлении услуги', 'danger');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            showNotification('Ошибка при обновлении услуги', 'danger');
        }
    });
}

/**
 * Инициализация кнопок активации/деактивации услуг
 */
function initToggleStatusButtons() {
    const toggleButtons = document.querySelectorAll('.toggle-status-btn');
    
    toggleButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const serviceId = this.getAttribute('data-service-id');
            const row = this.closest('tr');
            const serviceName = row.querySelector('.service-name').textContent;
            
            // Запрос подтверждения
            const isActive = row.classList.contains('inactive-service');
            const action = isActive ? 'активировать' : 'деактивировать';
            
            if (!confirm(`Вы уверены, что хотите ${action} услугу "${serviceName}"?`)) {
                return;
            }
            
            try {
                const response = await fetch(`/services/${serviceId}`, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    showNotification(data.message, 'success');
                    
                    // Перезагружаем страницу для обновления списка
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    showNotification(data.message || 'Ошибка при изменении статуса услуги', 'danger');
                }
            } catch (error) {
                console.error('Ошибка:', error);
                showNotification('Ошибка при изменении статуса услуги', 'danger');
            }
        });
    });
}

/**
 * Показ всплывающего уведомления
 */
function showNotification(message, type = 'info') {
    // Создаем контейнер для уведомлений, если его нет
    let container = document.getElementById('notifications-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notifications-container';
        container.style.position = 'fixed';
        container.style.top = '20px';
        container.style.right = '20px';
        container.style.zIndex = '9999';
        container.style.minWidth = '300px';
        document.body.appendChild(container);
    }

    // Создаем уведомление
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.role = 'alert';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    container.appendChild(notification);

    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 150);
    }, 5000);
}

