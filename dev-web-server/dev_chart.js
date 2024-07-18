document.addEventListener('DOMContentLoaded', function() {
    fetch('/random-floats')
        .then(response => response.json())
        .then(responseData => {
            const { data, labels, index_labels } = responseData;
            const chartWrapper = document.getElementById('chart-wrapper');
            data.forEach((list, index) => {
                // Create a container for each chart with a label
                const container = document.createElement('div');
                container.className = 'chart-container';

                const label = document.createElement('h2');
                label.textContent = labels[index];
                container.appendChild(label);

                const canvas = document.createElement('canvas');
                canvas.id = `chart-${index}`;
                container.appendChild(canvas);
                chartWrapper.appendChild(container);

                // Create a line chart with the random floats
                const ctx = canvas.getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: index_labels[index],
                        datasets: [{
                            label: labels[index],
                            data: list,
                            backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 1,
                            fill: false
                        }]
                    },
                    options: {
                        scales: {
                            x: {
                                type: 'time',
                                time: {
                                    unit: 'minute',
                                    displayFormats: {
                                        minute: 'HH:mm'
                                    },
                                    tooltipFormat: 'HH:mm'
                                },
                                ticks: {
                                    autoSkip: false,
                                    source: 'labels'
                                },
                                title: {
                                    display: true,
                                    text: 'Time (HH:mm)'
                                }
                            },
                            //y: {
                            //    title: {
                            //        display: true,
                            //        text: 'Value'
                            //    }
                            //}
                        }
                    }
                });
            });
        })
        .catch(error => console.error('Error fetching data:', error));
});
