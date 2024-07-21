/*
Copyright 2024 Hex-Software Oy

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

document.addEventListener("DOMContentLoaded", function() {
    sensor_count = 6
    //fetch('/sensor_meta')
    //    .then(response => response.json())
    //    .then(responseData => {
    //        console.log("response data:", responseData)
    //        sensor_count = responseData.count
    //    })
    
    console.log("HARDCODED sensor count:", sensor_count)
    const chartWrapper = document.getElementById('chart-wrapper')
    for (let i = 0; i < sensor_count; i++) {
        fetch('/sensor_data?sensor_index=' + i)
            .then(response => response.json())
            .then(responseData => {
                console.log("response data:", i, responseData)
            
                const container = document.createElement('div');
                container.className = responseData.type;
                const label = document.createElement('h2');
                label.textContent = responseData.type;
                container.appendChild(label);

                const canvas = document.createElement('canvas');
                canvas.id = `chart-${i}`;
                container.appendChild(canvas);
                chartWrapper.appendChild(container);

                const ctx = canvas.getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: responseData.times,
                        datasets: [{
                            label: responseData.type,
                            data: responseData.values,
                            //backgroundColor: 'rgba(75, 192, 192, 0.2)',
                            //borderColor: 'rgba(75, 192, 192, 1)',
                            //borderWidth: 1,
                            //fill: false
                        }]
                    },
                    options: {
                        /*plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(tooltipItem) {
                                        const date = new Date(tooltipItem.raw * 1000); // Convert Unix timestamp to milliseconds
                                        return date.getHours() + ':' + date.getMinutes();
                                    }
                                }
                            }
                        },*/
                        scales: {
                            /* TODO: render x-axis as Hours:Minutes instead of Unix timestamps
                            x: {
                                type: 'time',
                                time: {
                                    unit: 'minute',
                                    tooltipFormat: 'HH:mm', // Format for tooltip
                                    displayFormats: {
                                        minute: 'HH:mm' // Format for x-axis
                                    }
                                },
                                ticks: {
                                    callback: function(value, index, values) {
                                        const date = new Date(value * 1000); // Convert Unix timestamp to milliseconds
                                        return date.getHours() + ':' + date.getMinutes();
                                    }
                                }
                            },*/
                            y: {
                                min: responseData.min,
                                max: responseData.max,
                            }
                        }
                    }
                })
            }).catch(error => console.error('Error fetching data', error))
    }
    /*
    fetch('/sensor_data')
        .then(response => response.json())
        .then(responseData => {
            console.log("response data:", responseData)
            const { values, times, type } = responseData
            const chartWrapper = document.getElementById('chart-wrapper')
            console.log("values:", values)

            //.forEach(())
        })
    */
})