document.querySelectorAll('.rating_form').forEach(form => {
    form.addEventListener('submit', function (e) {
        e.preventDefault(); 

        const productId = form.querySelector('input[name="product_id"]').value;
        const ratingValue = form.querySelector('input[name="rating_value"]:checked').value;

        fetch(form.action, {
            method: 'POST',
            headers: {
                'X-CSRFToken': form.querySelector('input[name="csrfmiddlewaretoken"]').value,
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams({
                'product_id': productId,
                'rating_value': ratingValue,
            }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console(`Рейтинг для продукта ${data.product_name} обновлен!`);
            } else {
                alert(data.message); 
            }
        })
        .catch(error => console.error('Ошибка:', error));
    });
});
