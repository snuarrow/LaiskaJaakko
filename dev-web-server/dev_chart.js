document.addEventListener('DOMContentLoaded', function() {
    fetch('/random-floats')
        .then(response => response.json())
        .then(data => {
            // Create a histogram data
            const ctx = document.getElementById('myChart').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: Array.from({ length: data.length }, (_, i) => i + 1),
                    datasets: [{
                        label: 'Random Floats',
                        data: data,
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        borderColor: 'rgba(75, 192, 192, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: 'Index'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Value'
                            }
                        }
                    }
                }
            });
        });
});
