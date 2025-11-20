// JavaScript для страницы расходов

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация
    initAddExpenseForm();
    initEditExpenseButtons();
    initDeleteButtons();
});

/**
 * Инициализация формы добавления расхода
 */
function initAddExpenseForm() {
    const form = document.getElementById('addExpenseForm');
    if (!form) return;
    
    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const formData = new FormData(form);
        
        try {
            const response = await fetch('/expenses/create', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                showNotification('Расход успешно создан', 'success');
                
                // Закрыть модальное окно
                const modal = bootstrap.Modal.getInstance(document.getElementById('addExpenseModal'));
                modal.hide();
                
                // Перезагрузить страницу
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showNotification('Ошибка: ' + data.message, 'danger');
            }
        } catch (error) {
            console.error('Ошибка при создании расхода:', error);
            showNotification('Ошибка при создании расхода', 'danger');
        }
    });
}

/**
 * Инициализация кнопок редактирования расходов
 */
function initEditExpenseButtons() {
    const editButtons = document.querySelectorAll('.edit-expense');
    
    editButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const expenseId = this.getAttribute('data-expense-id');
            
            try {
                // Получить данные расхода
                const response = await fetch(`/expenses/list`);
                const data = await response.json();
                
                const expense = data.expenses.find(e => e.id == expenseId);
                if (expense) {
                    // Заполнить форму редактирования
                    document.getElementById('edit_expense_id').value = expense.id;
                    document.getElementById('edit_apartment_title').value = expense.apartment_title || '';
                    document.getElementById('edit_expense_date').value = expense.expense_date;
                    document.getElementById('edit_amount').value = expense.amount;
                    document.getElementById('edit_category').value = expense.category || '';
                    document.getElementById('edit_comment').value = expense.comment || '';
                    
                    // Открыть модальное окно
                    const modal = new bootstrap.Modal(document.getElementById('editExpenseModal'));
                    modal.show();
                }
            } catch (error) {
                console.error('Ошибка при получении данных расхода:', error);
                showNotification('Ошибка при получении данных расхода', 'danger');
            }
        });
    });
    
    // Обработчик формы редактирования
    const editForm = document.getElementById('editExpenseForm');
    if (editForm) {
        editForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const expenseId = document.getElementById('edit_expense_id').value;
            const formData = new FormData(editForm);
            
            try {
                const response = await fetch(`/expenses/${expenseId}`, {
                    method: 'PUT',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    showNotification('Расход успешно обновлен', 'success');
                    
                    // Закрыть модальное окно
                    const modal = bootstrap.Modal.getInstance(document.getElementById('editExpenseModal'));
                    modal.hide();
                    
                    // Перезагрузить страницу
                    setTimeout(() => {
                        window.location.reload();
                    }, 1000);
                } else {
                    showNotification('Ошибка: ' + data.message, 'danger');
                }
            } catch (error) {
                console.error('Ошибка при обновлении расхода:', error);
                showNotification('Ошибка при обновлении расхода', 'danger');
            }
        });
    }
}

/**
 * Инициализация кнопок удаления расходов
 */
function initDeleteButtons() {
    const deleteButtons = document.querySelectorAll('.delete-expense');
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', async function() {
            const expenseId = this.getAttribute('data-expense-id');
            
            if (!confirm('Вы уверены, что хотите удалить этот расход?')) {
                return;
            }
            
            try {
                const response = await fetch(`/expenses/${expenseId}`, {
                    method: 'DELETE'
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    showNotification('Расход удален', 'success');
                    
                    // Удалить строку из таблицы
                    const row = document.querySelector(`tr[data-expense-id="${expenseId}"]`);
                    if (row) {
                        row.remove();
                    }
                    
                    // Проверить, есть ли еще записи
                    const tbody = document.getElementById('expensesTableBody');
                    if (tbody && tbody.querySelectorAll('tr').length === 0) {
                        tbody.innerHTML = '<tr><td colspan="6" class="text-center">Нет данных для отображения</td></tr>';
                    }
                } else {
                    showNotification('Ошибка: ' + data.message, 'danger');
                }
            } catch (error) {
                console.error('Ошибка при удалении расхода:', error);
                showNotification('Ошибка при удалении расхода', 'danger');
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