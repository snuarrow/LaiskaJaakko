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

async function fetchWithRetry(url, options = {}, retries = 3, backoff = 3000) {
    try {
        const response = await fetch(url, options);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return response; // or response.json() if you want to parse the JSON body
    } catch (error) {
        if (retries > 0) {
            console.log(`Retrying... attempts left: ${retries}`);
            await new Promise((resolve) => setTimeout(resolve, backoff)); // wait before retrying
            return fetchWithRetry(url, options, retries - 1, backoff * 2); // retry with exponential backoff
        } else {
            throw new Error(`Max retries reached. Error: ${error.message}`);
        }
    }
}

const charts = []
const sensor_count = 6

function loadSensorData() {
    const chartWrapper = document.getElementById('chart-wrapper')
    if (charts.length !== sensor_count) {
        for (let i = 0; i < sensor_count; i++) {
            console.log("creating chart", i);
            const container = document.createElement('div');
            //container.className = "responseData.type";
            //const label = document.createElement('h2');
            //label.textContent = "responseData.type";
            //container.appendChild(label);
            const canvas = document.createElement('canvas');
            canvas.id = `chart-${i}`;
            container.appendChild(canvas);
            chartWrapper.appendChild(container);
            const ctx = canvas.getContext('2d');
            let chart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: [0,1,2],
                    datasets: [{
                        label: 'sensor',
                        data: [],
                    }]
                },
                options: {
                    scales: {
                        y: {
                            min: 0,
                            max: 100
                        }
                    }
                }
            })
            charts.push(chart);
            console.log("created chart", i)
        }
    }
    for (let i = 0; i < sensor_count; i++) {
        fetchWithRetry('/sensor_data?sensor_index=' + i, { method: 'GET' })
            .then(response => response.json())
            .then(responseData => {
                //if (responseData.type === 'MH-Moisture') {
                //    charts[i].data.datasets[i].data = responseData.values;
                //    charts[i].data.datasets[i].label = responseData.name;
                //} else {
                //    charts[i].data.datasets[0].data = responseData.values;
                //    charts[i].data.datasets[0].label = responseData.name;
                //}
                console.log("response data:", i, responseData)
                charts[i].data.labels = responseData.times;
                charts[i].options.scales.y.min = responseData.min;
                charts[i].options.scales.y.max = responseData.max;
                charts[i].data.datasets[0].data = responseData.values;
                charts[i].data.datasets[0].label = responseData.name;
                charts[i].update();
            }).catch(error => console.error('Error fetching data', error))
    }
}

document.addEventListener("DOMContentLoaded", function() {
    loadSensorData()
})

setTimeout(function(){
    setInterval(loadSensorData, 60000);
}, 2000)