document.getElementById('employees-form').addEventListener('submit', async (event) => {
    event.preventDefault(); // Предотвращаем перезагрузку страницы

    const inputElement = document.getElementById('employee-data-input');
    const nameEmployee = inputElement.value;

    // Формируем объект (Payload)
    const payload = {
        name: nameEmployee
    };

    try {
        // Отправляем POST-запрос с JSON-payload
        const response = await fetch('/employees', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json' // Говорим серверу, что это JSON
            },
            body: JSON.stringify(payload) // Превращаем объект в строку JSON
        });

        if (response.ok) {
            const result = await response.json();
            alert(`Сервер принял payload! Имя сотрудника: ${result.name}`);
            inputElement.value = ''; // Очищаем поле ввода
        } else {
            console.error('Ошибка сервера:', response.status);
        }
    } catch (error) {
        console.error('Ошибка сети:', error);
    }
});