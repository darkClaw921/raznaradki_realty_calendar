// JavaScript для страницы управления планами

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация
    initAddPlanForm();
    initPlanList();
    initEditPlanButtons();
    initDeletePlanButtons();
});

/**
 * Инициализация формы добавления/редактирования плана
 */
function initAddPlanForm() {
    const form = document.getElementById('addPlanForm');
    const modalTitle = document.getElementById('addPlanModalLabel');
    const planIdInput = document.getElementById('plan_id');
    if (!form || !modalTitle || !planIdInput) return;
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        const planId = planIdInput.value;
        const url = planId ? `/plans/${planId}` : '/plans/create';
        const method = planId ? 'PUT' : 'POST';
        
        try {
            const response = await fetch(url, {
                method: method,
                body: formData
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                showNotification(planId ? 'План обновлен' : 'План создан', 'success');
                
                // Закрыть модальное окно и очистить форму
                const modal = bootstrap.Modal.getInstance(document.getElementById('addPlanModal'));
                modal.hide();
                form.reset();
                planIdInput.value = '';
                modalTitle.textContent = 'Добавить план';
                
                // Перезагрузить страницу
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification('Ошибка: ' + data.message, 'danger');
            }
        } catch (error) {
            console.error('Ошибка при сохранении плана:', error);
            showNotification('Ошибка при сохранении плана', 'danger');
        }
    });
    
    // Обработчик показа модалки для очистки
    const modalElement = document.getElementById('addPlanModal');
    if (modalElement) {
        modalElement.addEventListener('hidden.bs.modal', function () {
            form.reset();
            planIdInput.value = '';
            modalTitle.textContent = 'Добавить план';
        });
    }
}

/**
 * Инициализация списка планов (загрузка через AJAX для динамики)
 */
function initPlanList() {
    loadPlans();
}

async function loadPlans() {
    try {
        const response = await fetch('/plans/list');
        const data = await response.json();
        
        const tbody = document.getElementById('plansTableBody');
        if (!tbody) return;
        
        if (data.plans && data.plans.length > 0) {
            tbody.innerHTML = data.plans.map(plan => `
                <tr data-plan-id="${plan.id}">
                    <td class="period-column">${new Date(plan.start_date).toLocaleDateString('ru-RU')} - ${new Date(plan.end_date).toLocaleDateString('ru-RU')}</td>
                    <td style="text-align: right;">${formatNumber(plan.target_amount)}</td>
                    <td class="actions-column">
                        <button type="button" class="btn btn-warning btn-sm edit-plan" data-plan-id="${plan.id}" data-start-date="${plan.start_date}" data-end-date="${plan.end_date}" data-target-amount="${plan.target_amount}">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button type="button" class="btn btn-danger btn-sm delete-plan ms-1" data-plan-id="${plan.id}">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                </tr>
            `).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center">Нет планов</td></tr>';
        }
        
        // Переинициализировать кнопки после загрузки
        initEditPlanButtons();
        initDeletePlanButtons();
    } catch (error) {
        console.error('Ошибка при загрузке планов:', error);
        showNotification('Ошибка при загрузке планов', 'danger');
    }
}

/**
 * Инициализация кнопок редактирования планов
 */
function initEditPlanButtons() {
    const editButtons = document.querySelectorAll('.edit-plan');
    
    editButtons.forEach(button => {
        button.addEventListener('click', function() {
            const planId = this.getAttribute('data-plan-id');
            const startDate = this.getAttribute('data-start-date');
            const endDate = this.getAttribute('data-end-date');
            const targetAmount = this.getAttribute('data-target-amount');
            
            document.getElementById('plan_id').value = planId;
            document.getElementById('start_date').value = startDate;
            document.getElementById('end_date').value = endDate;
            document.getElementById('target_amount').value = targetAmount;
            
            const modalTitle = document.getElementById('addPlanModalLabel');
            modalTitle.textContent = 'Редактировать план';
            
            const modal = new bootstrap.Modal(document.getElementById('addPlanModal'));
            modal.show();
        });
    });
}

/**
 * Инициализация кнопок удаления планов
 */
function initDeletePlanButtons() {
    const deleteButtons = document.querySelectorAll('.delete-plan');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const planId = this.getAttribute('data-plan-id');
            
            if (!confirm('Вы уверены, что хотите удалить этот план?')) {
                return;
            }
            
            try {
                const response = await fetch(`/plans/${planId}`, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    showNotification('План удален', 'success');
                    
                    // Удалить строку из таблицы
                    const row = this.closest('tr');
                    if (row) {
                        row.remove();
                    }
                    
                    // Проверить, есть ли еще записи
                    const tbody = document.getElementById('plansTableBody');
                    if (tbody && tbody.querySelectorAll('tr').length === 0) {
                        tbody.innerHTML = '<tr><td colspan="3" class="text-center">Нет планов</td></tr>';
                    }
                } else {
                    showNotification('Ошибка: ' + data.message, 'danger');
                }
            } catch (error) {
                console.error('Ошибка при удалении плана:', error);
                showNotification('Ошибка при удалении плана', 'danger');
            }
        });
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