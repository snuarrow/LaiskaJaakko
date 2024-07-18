document.addEventListener('DOMContentLoaded', function() {
    fetch('/random-floats')
        .then(response => response.json())
        .then(data => {
            const chartWrapper = document.getElementById('chart-wrapper');
            console.log("data:", data);
            data.forEach((list, index) => {
                // Create a container for each chart
                const container = document.createElement('div');
                container.className = 'chart-container';
                const canvas = document.createElement('canvas');
                canvas.id = `chart-${index}`;
                container.appendChild(canvas);
                chartWrapper.appendChild(container);

                // Create a bar chart with the random floats
                const ctx = canvas.getContext('2d');
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: list.map((_, i) => `Item ${i + 1}`),
                        datasets: [{
                            label: `Random Floats ${index + 1}`,
                            data: list,
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
        })
        .catch(error => console.error('Error fetching data:', error));
});
