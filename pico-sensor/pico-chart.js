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

console.log("script running: chartName chartPath initDelayMS");
let chartName = new Chart(document.getElementById('chartName').getContext('2d'), {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'chartLabel',
            data: [0,2,0,1,0,2,0,1,0,2],
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1
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
});
function fetchData_chartName() {
    console.log("fetchData() chartName")
    fetch('/chartPath')
        .then(response => response.json())
        .then(data => {
            chartName.data.labels = data.labels;
            chartName.data.datasets[0].data = data.values;
            chartName.update();
        })
        .catch(error => {
            console.log("failed to fetch /chartPath, error:", error);
        })
}
document.addEventListener('visibilitychange', function() {
    if (document.visibilityState === 'visible') {
        chartName.update();
    }
});
setTimeout(function(){
    fetchData_chartName();
    setInterval(fetchData_chartName, 60000);
}, initDelayMS)
