document.addEventListener('DOMContentLoaded', function () {
    initEditButtons();
    initToggleStatusButtons();
    initSaveButton();
});

function initEditButtons() {
    const editButtons = document.querySelectorAll('.btn-edit');
    const modalElement = document.getElementById('editRealtyModal');
    const modal = new bootstrap.Modal(modalElement);

    editButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            const row = this.closest('tr');
            const id = row.getAttribute('data-id');
            const name = row.querySelector('.realty-name').textContent.trim();

            document.getElementById('editRealtyId').value = id;
            document.getElementById('editRealtyName').value = name;

            modal.show();
        });
    });
}

function initSaveButton() {
    const saveBtn = document.getElementById('saveRealtyBtn');

    saveBtn.addEventListener('click', function () {
        const id = document.getElementById('editRealtyId').value;
        const name = document.getElementById('editRealtyName').value;

        if (!name.trim()) {
            showNotification('Название не может быть пустым', 'danger');
            return;
        }

        const formData = new FormData();
        formData.append('name', name);

        fetch(`/realty/${id}`, {
            method: 'PUT',
            body: formData
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showNotification('Объект обновлен', 'success');
                    setTimeout(() => location.reload(), 1000);
                } else {
                    showNotification(data.message || 'Ошибка при обновлении', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Ошибка сети', 'danger');
            });
    });
}

function initToggleStatusButtons() {
    const toggleButtons = document.querySelectorAll('.btn-toggle-status');

    toggleButtons.forEach(btn => {
        btn.addEventListener('click', function () {
            const row = this.closest('tr');
            const id = row.getAttribute('data-id');
            const isDeactivating = btn.classList.contains('btn-danger');
            const action = isDeactivating ? 'деактивировать' : 'активировать';

            if (confirm(`Вы уверены, что хотите ${action} этот объект?`)) {
                fetch(`/realty/${id}`, {
                    method: 'DELETE'
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            showNotification('Статус обновлен', 'success');
                            setTimeout(() => location.reload(), 500);
                        } else {
                            showNotification(data.message || 'Ошибка при изменении статуса', 'danger');
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        showNotification('Ошибка сети', 'danger');
                    });
            }
        });
    });
}

function showNotification(message, type = 'success') {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    alertDiv.style.zIndex = '9999';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);

    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}
